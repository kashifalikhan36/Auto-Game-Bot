"""
Complete rewrite of FH5 decision_rules, constraints, situation_checklist, and game_context.
Goal: drive like a real human -- smooth inputs, look ahead, brake before corners, FULL_THROTTLE default.
Preserves: named_actions, named_action_descriptions, key_map, action_list, behaviors, etc.
"""
import json, pathlib

p = pathlib.Path("games_config/forza_horizon_5/config.json")
cfg = json.loads(p.read_text(encoding="utf-8"))

# ══════════════════════════════════════════════════════════════════════════════
# GAME CONTEXT  (clean up stale Rewind references, add real-driver philosophy)
# ══════════════════════════════════════════════════════════════════════════════
cfg["game_context"] = """\
Forza Horizon 5 (FH5) -- open-world racing game set in Mexico. You are an AI racing driver controlling a car with keyboard inputs (WASD layout).

KEY BINDINGS:
  W = Accelerate (hold for throttle)
  S = Brake / Reverse (tap to brake, hold to reverse)
  A = Steer Left
  D = Steer Right
  E = Shift Up (manual gearbox)
  Q = Shift Down (manual gearbox)
  Space = Handbrake (locks rear wheels -- for drift entry or tight U-turns)
  Tab = Change Camera View
  H = Horn
  Enter = Activate / Accept

IMPORTANT -- KEYBOARD PHYSICS:
  Keyboard inputs are digital (fully on or fully off). Hold duration controls effect:
  - Short tap A/D (100-200ms) = micro-correction, barely any yaw
  - Medium hold A/D (300-500ms) = gentle curve tracking
  - Long hold A/D (700ms+) = significant turn, only for tight corners
  Too much steering input = understeer (front pushes wide) or oversteer (rear slides out).
  Always use the minimum steering input needed. Smooth > aggressive.

GAME MODES:
  Road Racing / Street Scene -- follow the racing line on tarmac
  Cross Country / Dirt Racing -- rough terrain, no road to stay on
  Drag Race -- short straight sprint, shift at red-line RPM
  Freeroam -- open world, watch for civilian traffic

PR STUNTS (skill zones):
  Speed Trap   -- blue lightning bolt -- hit max speed at camera
  Danger Sign  -- skull icon -- jump ramp, never brake before it
  Drift Zone   -- orange S-curves -- score drift points through the zone
  Drag Race    -- christmas-tree light sequence

RACING LINE:
  Magenta / coloured line on road shows optimal path.
  GREEN section = safe to go fast, keep throttle on
  ORANGE section = lift throttle slightly, corner is coming
  RED section = brake now, corner is tight
  Classic line: wide entry → tight apex → wide exit

REAL DRIVER MINDSET:
  A real racing driver thinks 3-5 seconds AHEAD of the car, not at the current frame.
  The default state is FULL_THROTTLE on clear roads. Only deviate with a specific visual reason.
  Corners follow a 5-step process: SPOT → BRAKE POINT → TURN-IN → APEX → ACCELERATE OUT.
  Smooth inputs always beat aggressive jerky ones. One decisive action per frame.
  Reverse is a last resort used under 1% of the time -- only when completely stopped and blocked.\
"""

# ══════════════════════════════════════════════════════════════════════════════
# DECISION RULES  (complete rewrite -- real driver priority order)
# ══════════════════════════════════════════════════════════════════════════════
cfg["decision_rules"] = """\
=== REAL DRIVER DECISION FRAMEWORK ===
Think like a professional racing driver. Work through these rules TOP TO BOTTOM.
Stop at the FIRST rule that matches what you see. One action per frame.

────────────────────────────────────────────────────────────────────────────────
RULE 1 -- MENU / LOADING / CUTSCENE  [ALWAYS check first]:
  If ANY of: loading bar, black transition screen, cutscene, XP/reward screen,
  menu open, race results, paused, or white-text overlay fills the screen
  => DO_NOTHING

────────────────────────────────────────────────────────────────────────────────
RULE 2 -- SPIN / FACING WRONG DIRECTION  [check before anything else]:
  ONLY applies when the car has visibly pivoted so the nose points 90+ degrees
  away from the intended road direction AND car speed is very low or zero.
  (If still moving forward -- even off road -- skip to RULE 4 instead.)

  Car nose swung LEFT (counterclockwise spin), road is to the RIGHT of the nose:
  => SPIN_RECOVER_LEFT   (W + D together -- throttle + right countersteer)
  Car nose swung RIGHT (clockwise spin), road is to the LEFT of the nose:
  => SPIN_RECOVER_RIGHT  (W + A together -- throttle + left countersteer)

────────────────────────────────────────────────────────────────────────────────
RULE 3 -- COMPLETELY STOPPED AGAINST A WALL / BARRIER  [reverse only here]:
  ONLY applies when: speedometer reads zero, W pressed gives no forward movement,
  and a wall / barrier / rock is visibly blocking the front of the car.
  This rule is rare -- under 2% of frames. Do not trigger it unless truly stopped.

  Open space behind on the LEFT (steer A while reversing):
  => UNSTICK_REVERSE_LEFT
  Open space behind on the RIGHT (steer D while reversing):
  => UNSTICK_REVERSE_RIGHT
  No clear direction visible -- reverse straight first then re-assess:
  => UNSTICK_REVERSE

────────────────────────────────────────────────────────────────────────────────
RULE 4 -- OFF ROAD IN A ROAD/STREET RACE  [grass/dirt under tyres]:
  Applies when: grass, dirt, gravel or sand is clearly visible UNDER the car,
  AND this is a Road Race or Street Scene event (NOT cross-country or dirt race).
  Goal: SLOW DOWN → REALIGN → RETURN TO TARMAC → BUILD SPEED AGAIN.

  How far off the road?

  BARELY OFF (road edge beside the car, 1-2 wheels on grass, car still moving):
    Road is to the LEFT -- steer gently left back onto tarmac:
    => ROAD_NUDGE_LEFT
    Road is to the RIGHT -- steer gently right back onto tarmac:
    => ROAD_NUDGE_RIGHT

  SIGNIFICANTLY OFF (more than half the car is off tarmac, car still moving):
    Road clearly to the LEFT of the car:
    => ROAD_RETURN_LEFT   (brake briefly → steer left → re-accelerate)
    Road clearly to the RIGHT of the car:
    => ROAD_RETURN_RIGHT  (brake briefly → steer right → re-accelerate)

  DEEPLY OFF / BOUNCED OFF BARRIER (car is far from tarmac or has stopped):
    Road is to the LEFT after recovering:
    => ROAD_RECOVER_LEFT  (hard brake → turn left → build speed on road)
    Road is to the RIGHT after recovering:
    => ROAD_RECOVER_RIGHT (hard brake → turn right → build speed on road)

  AFTER RETURNING TO TARMAC:
    All four wheels back on asphalt? Immediately switch BACK to normal driving:
    THROTTLE_LIGHT (1 frame) → THROTTLE_MEDIUM (1-2 frames) → FULL_THROTTLE
    Do NOT keep using road-return actions once tyres are on asphalt.

────────────────────────────────────────────────────────────────────────────────
RULE 5 -- PR STUNT: SPEED TRAP  (blue lightning bolt icon visible ahead):
  Speed trap camera on a straight ahead, road is clear and straight:
  => SPEED_TRAP_BLAST   (hold full throttle all the way through)
  Speed trap but road curves LEFT into it:
  => ACCEL_LEFT_GENTLE  (track the curve at speed, don't sacrifice momentum)
  Speed trap but road curves RIGHT into it:
  => ACCEL_RIGHT_GENTLE

────────────────────────────────────────────────────────────────────────────────
RULE 6 -- PR STUNT: DANGER SIGN / JUMP RAMP  (skull icon or ramp ahead):
  Ramp directly ahead -- line up straight and approach flat out:
  => JUMP_APPROACH
  Ramp ahead, car is slightly LEFT of centre line:
  => ACCEL_RIGHT_GENTLE  (steer to align, keep throttle on)
  Ramp ahead, car is slightly RIGHT of centre line:
  => ACCEL_LEFT_GENTLE

────────────────────────────────────────────────────────────────────────────────
RULE 7 -- PR STUNT: DRIFT ZONE  (orange S-curve arrows or drift score visible):
  Entering drift zone, zone bends to the LEFT:
  => DRIFT_ZONE_LEFT
  Entering drift zone, zone bends to the RIGHT:
  => DRIFT_ZONE_RIGHT
  Mid-drift, car sliding LEFT (nose pointing left, tail out right):
  => DRIFT_MAINTAIN_LEFT   (countersteer right + throttle to hold angle)
  Mid-drift, car sliding RIGHT (nose pointing right, tail out left):
  => DRIFT_MAINTAIN_RIGHT  (countersteer left + throttle to hold angle)

────────────────────────────────────────────────────────────────────────────────
RULE 8 -- DRAG RACE  (drag strip / christmas tree launch sequence visible):
  Countdown lights still showing (not green yet):
  => DO_NOTHING   (wait for green light, don't burn clutch)
  Green light just appeared / race just launched:
  => DRAG_LAUNCH  (clutch-kick launch for best 0-60)
  On the strip, straight ahead, no corners, race in progress:
  => DRAG_FULL_THROTTLE
  RPM gauge at red-line (needle far right), manual gearbox:
  => SHIFT_UP_ACCELERATE

────────────────────────────────────────────────────────────────────────────────
RULE 9 -- IMMINENT COLLISION (wall / barrier / car less than 1 second away):
  Object DIRECTLY ahead, no time or space to steer -- unavoidable:
  => EMERGENCY_BRAKE   (S + Space -- maximum stopping force)
  Object ahead, clear escape space visible to the LEFT:
  => SWERVE_LEFT_FULL  (emergency steer left)
  Object ahead, clear escape space visible to the RIGHT:
  => SWERVE_RIGHT_FULL (emergency steer right)

────────────────────────────────────────────────────────────────────────────────
RULE 10 -- OPPONENT CAR BLOCKING RACING LINE:
  Opponent car directly ahead, space clearly open on the LEFT:
  => OVERTAKE_LEFT   (W + A -- accelerate and move left past them)
  Opponent car directly ahead, space clearly open on the RIGHT:
  => OVERTAKE_RIGHT  (W + D -- accelerate and move right past them)
  Opponent ahead but no gap yet -- stay in their slipstream for the speed boost:
  => FULL_THROTTLE   (sit close, wait for a gap to appear)

────────────────────────────────────────────────────────────────────────────────
RULE 11 -- CORNER / CURVE AHEAD  (road edge itself bends, not just racing line):

  STEP 1 -- READ THE RACING LINE COLOUR (most reliable corner signal):
    RED strip ahead   = brake zone -- brake NOW before turning
    ORANGE strip      = lift zone  -- reduce throttle, corner soon
    GREEN strip       = acceleration zone -- stay on throttle through this section

  STEP 2 -- ASSESS CORNER TYPE based on how tight the road bends:
    SWEEPING CURVE   : road barely curves, lots of tarmac visible ahead (GENTLE)
    STANDARD CORNER  : road turns ~45-90 degrees, clear exit (MEDIUM)
    TIGHT CORNER     : road turns >90 degrees, exit barely visible (TIGHT)
    HAIRPIN / U-TURN : road turns back on itself, sharp exit (HAIRPIN)

  STEP 3 -- PICK THE RIGHT ACTION:

  SWEEPING LEFT (GREEN line, road barely curves left):
  => ACCEL_LEFT_GENTLE   (hold W+A 220ms -- short steer tap, maintain speed)

  STANDARD LEFT (ORANGE/RED line, clear left bend):
  => ACCEL_LEFT_MEDIUM   (brake slightly then W+A through the corner)

  TIGHT LEFT already in corner (ORANGE line reaching right entry):
  => CORNER_BRAKE_EXIT_LEFT  (brake on entry, steer left, throttle on exit)

  HAIRPIN LEFT (RED line, very little exit visible):
  => BRAKE_STEER_LEFT    (hard brake, tight left steer, then ACCEL_LEFT_TIGHT on exit)

  SWEEPING RIGHT (GREEN line, barely curves right):
  => ACCEL_RIGHT_GENTLE  (hold W+D 220ms -- short steer tap, maintain speed)

  STANDARD RIGHT (ORANGE/RED line, clear right bend):
  => ACCEL_RIGHT_MEDIUM

  TIGHT RIGHT already in corner:
  => CORNER_BRAKE_EXIT_RIGHT

  HAIRPIN RIGHT:
  => BRAKE_STEER_RIGHT   (then ACCEL_RIGHT_TIGHT on exit)

  CORNER TECHNIQUE -- real driver rules:
  - BRAKE BEFORE the corner entry, NOT while steering through it
  - Turn in AFTER braking, not at the same time (except trail braking on smooth corners)
  - Hit the APEX (inside edge of the corner) then open throttle progressively to the exit
  - On exit: THROTTLE_LIGHT → THROTTLE_MEDIUM → FULL_THROTTLE as road straightens

────────────────────────────────────────────────────────────────────────────────
RULE 12 -- GEAR CHANGE  (only if manual gearbox telemetry is visible on screen):
  RPM gauge needle in the RED zone (far right), gear can be raised:
  => SHIFT_UP
  Engine lugging (RPM very low after braking into a corner):
  => SHIFT_DOWN
  Exiting corner, need smooth power delivery while upshifting:
  => SHIFT_UP_ACCELERATE

────────────────────────────────────────────────────────────────────────────────
RULE 13 -- CROSS COUNTRY / DIRT RACE EVENT  (off-road terrain expected):
  No asphalt visible, rough terrain, cross-country checkpoints shown on map.
  Path clear ahead -- drive on:
  => OFFROAD_THROTTLE
  Rock / tree / fence on the RIGHT, go around to the left:
  => OFFROAD_LEFT
  Rock / tree / fence on the LEFT, go around to the right:
  => OFFROAD_RIGHT
  Very rough section (rocks, steep slope, river, deep ruts) -- pick way carefully:
  => OFFROAD_CAREFUL

────────────────────────────────────────────────────────────────────────────────
RULE 14 -- CIVILIAN TRAFFIC AHEAD  (freeroam only -- civilian car/truck in lane):
  Civilian vehicle in your lane, clear space to the LEFT:
  => SWERVE_LEFT
  Civilian vehicle in your lane, clear space to the RIGHT:
  => SWERVE_RIGHT

────────────────────────────────────────────────────────────────────────────────
RULE 15 -- STRAIGHT ROAD / DEFAULT  [*** MOST COMMON ANSWER -- ~80% of frames ***]:
  None of Rules 1-14 matched. Road is clear straight tarmac ahead.

  Clear straight road, no obstacles, no corners imminent:
  => FULL_THROTTLE   *** DEFAULT -- when in doubt, pick this ***

  Car is drifting slightly to the RIGHT of road centre on a straight (right tyres
  approaching right edge line) -- gentle micro-correction:
  => NUDGE_LEFT      (140ms tap A -- tiny yaw correction, W stays effective)

  Car is drifting slightly to the LEFT of road centre on a straight (left tyres
  approaching left edge line) -- gentle micro-correction:
  => NUDGE_RIGHT     (140ms tap D -- tiny yaw correction, W stays effective)

  Straight road but a corner is visible at the far end (not yet close enough for
  RULE 11) -- prepare early by easing off:
  => THROTTLE_MEDIUM (lift slightly, stay alert, assess corner on next frame)

  Just exited a corner, short straight connects to next bend:
  => THROTTLE_LIGHT  (build speed back up smoothly from corner exit)\
""".split("\n")

# ══════════════════════════════════════════════════════════════════════════════
# CONSTRAINTS  (clean rewrite -- no contradictions, real-driver logic)
# ══════════════════════════════════════════════════════════════════════════════
cfg["constraints"] = [
    "* NEVER use REWIND or REWIND_HOLD. Rewind is disabled. Recover manually with spin-correct or road-return actions.",

    # Forward-bias core
    "* DEFAULT ACTION IS FULL_THROTTLE. If no rule clearly matches, pick FULL_THROTTLE. The car must always move FORWARD.",
    "* NEVER use any reverse action (UNSTICK_REVERSE, REVERSE, REVERSE_LEFT, REVERSE_RIGHT, etc.) unless the car speedometer shows speed = 0 AND a wall physically blocks the front. This happens under 2% of frames.",
    "* If the car is moving at any speed -- even 5 km/h -- do NOT reverse. Keep W held and correct direction with A or D.",

    # Straight-road discipline
    "* On a STRAIGHT road: FULL_THROTTLE is correct for ~90% of frames. Use NUDGE_LEFT or NUDGE_RIGHT (140ms tap) for micro-corrections when drifting toward a road edge. Do NOT use ACCEL_*_GENTLE on straights -- that is for actual road curves only.",
    "* NEVER steer just because the racing line (magenta strip) shifts slightly. The racing line shows the ideal apex, not a target to chase on a straight. Only steer when the ROAD EDGE itself visibly curves.",
    "* NEVER alternate left-steer then right-steer on consecutive frames on a straight -- this causes oscillation and wastes lap time. After any steer correction, return to FULL_THROTTLE next frame unless the road continues to curve.",

    # Corner technique
    "* ALWAYS brake BEFORE turning into a corner -- not during. Brake in a straight line first, then steer. This prevents understeer.",
    "* NEVER brake with wheels fully turned (this causes understeer -- car pushes wide). Straighten very briefly before hard braking.",
    "* On corner EXIT: build throttle progressively -- THROTTLE_LIGHT first, then THROTTLE_MEDIUM, then FULL_THROTTLE as the road straightens. Never snap to full throttle from a tight corner -- it causes wheelspin/oversteer.",
    "* Use the RACING LINE COLOUR as your corner signal: GREEN = gas on, ORANGE = lift throttle, RED = brake now.",

    # Off-road recovery
    "* If off road (grass/dirt) in a road race: slow down first, steer back to tarmac, then re-accelerate. Never floor it on grass -- it makes the situation worse.",
    "* After any road-return or off-road recovery action: once all four tyres are back on asphalt, switch to THROTTLE_LIGHT then build up. Do NOT continue using road-return actions on tarmac.",

    # Safety limits
    "* NEVER use EMERGENCY_BRAKE unless a collision is truly unavoidable within the next second. It is faster to swerve than to brake in most scenarios.",
    "* NEVER use DRIFT_COMBO or HANDBRAKE on a straight at high speed -- instant spin risk.",
    "* NEVER pick JUMP_APPROACH unless a physical jump ramp is directly in front of the car.",
    "* NEVER pick SPEED_TRAP_BLAST on a curved road -- straighten first or risk crashing at full speed.",
    "* NEVER pick ACTIVATE unless an on-screen Enter/Accept button prompt is literally visible.",
    "* NEVER pick DO_NOTHING while a race is active and the car is in motion.",

    # Anti-loop protection
    "* If the same action has been chosen 3 or more frames in a row with no visible forward progress, switch to a DIFFERENT FORWARD ACTION (e.g. THROTTLE_LIGHT or NUDGE_* to find a new line). Never loop the same recovery action.",

    # General quality
    "* Smooth driving beats aggressive driving. One clean decisive action per frame. Avoid jerky corrections.",
    "* In a corner, always prefer a brake-then-steer sequence (CORNER_BRAKE_EXIT_*) over pure braking alone for tighter corners.",
]

# ══════════════════════════════════════════════════════════════════════════════
# SITUATION CHECKLIST  (clean, ordered, easy for LLM to work through)
# ══════════════════════════════════════════════════════════════════════════════
cfg["situation_checklist"] = [
    "Study the screenshot carefully. Answer these questions in strict order. Stop at the FIRST yes.",
    "  1.  Is there a loading screen, menu, cutscene, or results overlay?                  -> RULE 1  (DO_NOTHING)",
    "  2.  Has the car spun so the nose is 90+ degrees from the road AND speed is near zero?   -> RULE 2  (SPIN_RECOVER_*)",
    "  3.  Is speed = 0 AND a wall is physically blocking the front preventing any forward movement? -> RULE 3  (UNSTICK_REVERSE_*)",
    "  4.  Is grass/dirt/sand visible UNDER the car in a road race (not cross-country)?    -> RULE 4  (ROAD_NUDGE/RETURN/RECOVER_*)",
    "  5.  Is a SPEED TRAP blue lightning bolt visible on a straight ahead?                -> RULE 5  (SPEED_TRAP_BLAST)",
    "  6.  Is a DANGER SIGN jump ramp directly in front of the car?                        -> RULE 6  (JUMP_APPROACH)",
    "  7.  Are orange DRIFT ZONE arrows or a drift score counter on screen?                -> RULE 7  (DRIFT_ZONE_*/DRIFT_MAINTAIN_*)",
    "  8.  Is this a drag strip with a christmas-tree launch light?                        -> RULE 8  (DRAG_*)",
    "  9.  Is a wall/barrier/car less than 1 second away from hitting the car?             -> RULE 9  (EMERGENCY_BRAKE / SWERVE_*_FULL)",
    "  10. Is an opponent car directly blocking the racing line right in front?             -> RULE 10 (OVERTAKE_*)",
    "  11. Does the road edge itself visibly curve or bend ahead?                          -> RULE 11 (corner actions based on severity + racing line colour)",
    "  12. Is manual gearbox telemetry visible showing a gear change is needed?            -> RULE 12 (SHIFT_UP / SHIFT_DOWN)",
    "  13. Is this a cross-country or dirt event with no tarmac road?                      -> RULE 13 (OFFROAD_*)",
    "  14. Is there a civilian car or slow truck directly ahead in freeroam?               -> RULE 14 (SWERVE_LEFT / SWERVE_RIGHT)",
    "  15. None of the above matched -- clear road or corner managed:                      -> RULE 15 (FULL_THROTTLE is almost always correct here)",
    "Output EXACTLY ONE action name from the named action list. No explanation, just the action name.",
]

# ══════════════════════════════════════════════════════════════════════════════
# WRITE + VERIFY
# ══════════════════════════════════════════════════════════════════════════════
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"config.json updated  ({p.stat().st_size:,} bytes)")
print(f"  named_actions  : {len(cfg['named_actions'])}")
print(f"  decision_rules : {len(cfg['decision_rules'])} lines")
print(f"  constraints    : {len(cfg['constraints'])} items")
print(f"  checklist      : {len(cfg['situation_checklist'])} items")

r = "\n".join(cfg["decision_rules"])
c = "\n".join(cfg["constraints"])
checks = [
    ("RULE 1 menu",              "RULE 1" in r),
    ("RULE 2 spin",              "RULE 2" in r),
    ("RULE 3 stopped",           "RULE 3" in r),
    ("RULE 4 off road",          "RULE 4" in r),
    ("RULE 11 corners",          "RULE 11" in r),
    ("RULE 15 default",          "RULE 15" in r),
    ("Racing line colour guide", "RED strip" in r and "GREEN strip" in r),
    ("Brake before corner",      "BRAKE BEFORE" in r),
    ("No reverse constraint",    "speed = 0" in c),
    ("No oscillation constraint","oscillation" in c),
    ("No Rewind constraint",     "Rewind is disabled" in c),
    ("No stale ALWAYS Rewind",   "ALWAYS use Rewind" not in c),
    ("game_context clean",       "Rewind liberally" not in cfg["game_context"]),
    ("Forward bias in context",  "FULL_THROTTLE" in cfg["game_context"]),
]
print()
for label, ok in checks:
    print(f"  {'OK' if ok else 'FAIL'}  {label}")
