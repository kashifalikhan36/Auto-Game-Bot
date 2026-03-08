"""
Generates a complete Forza Horizon 5 config.json covering every driving
scenario: straight roads, corners, drifts, PR stunts, racing, overtaking,
traffic, off-road, crashes, menus.
"""
import json, pathlib

cfg = {
  "game_name": "Forza Horizon 5",
  "game_id": "forza_horizon_5",
  "description": "Full PC keyboard bindings for Forza Horizon 5 (WASD default layout). All named actions and decision rules for autonomous AI driving.",

  # ── GAME CONTEXT (injected into LLM system prompt) ────────────────────────
  "game_context": (
      "Forza Horizon 5 (FH5) -- open-world racing game set in Mexico. "
      "You are driving a car using keyboard controls (WASD layout). "
      "\n\nKEY BINDINGS:\n"
      "  W = Accelerate (full throttle when held)\n"
      "  S = Brake / Reverse\n"
      "  A = Steer Left\n"
      "  D = Steer Right\n"
      "  E = Shift Up (manual gearbox)\n"
      "  Q = Shift Down (manual gearbox)\n"
      "  Space = Handbrake (instant rear-wheel lock -- use for drift initiation)\n"
      "  Shift = Clutch\n"
      "  R = Rewind (undo the last few seconds -- use after crash or spin)\n"
      "  Tab = Change Camera View\n"
      "  H = Horn\n"
      "  M = Map\n"
      "  C = Anna AI assistant\n"
      "  Enter = Activate / Accept\n"
      "  Arrow keys = Look Left / Right / Back / Forward\n"
      "\nGAME MODES:\n"
      "  Road Racing  -- follow the racing line (magenta arrow/line on road)\n"
      "  Street Scene -- race on closed public roads\n"
      "  Cross Country -- rough terrain, dirt, rocks, rivers\n"
      "  Dirt Racing  -- gravel/dirt track events\n"
      "  Drag Race    -- short straight, shift at perfect RPM\n"
      "  Trial        -- convoy team event against AI drivatars\n"
      "  Playground / EventLab -- custom events\n"
      "  Freeroam     -- drive anywhere on the map\n"
      "\nPR STUNTS (special skill zones on the map):\n"
      "  Speed Trap   -- blue lightning bolt icon -- hit max speed at the camera\n"
      "  Speed Zone   -- sustain high average speed through a section\n"
      "  Danger Sign  -- skull icon -- hit a jump ramp at full speed for maximum distance\n"
      "  Drift Zone   -- orange S-curve arrows -- chain drift score through the zone\n"
      "  Trailblazer  -- follow a timed off-road trail\n"
      "\nDRIVING PHYSICS:\n"
      "  Keyboard inputs are digital (full on/off) -- hold duration controls how much turn/brake.\n"
      "  Too much steering = understeer/oversteer -- tap steer keys for gentle curves.\n"
      "  Handbrake (Space) at speed locks rear wheels instantly -- great for tight U-turns and drift entry.\n"
      "  Rewind (R) goes back 5-10 seconds -- safest recovery after crash, wall hit, or spin.\n"
      "  Manual shifting: shift up (E) at high RPM red-line, shift down (Q) before braking into corner.\n"
      "  Slipstream: follow closely behind opponent for speed boost, then pull out to overtake.\n"
      "\nRACING LINE:\n"
      "  The pink/magenta arrow or coloured line on road shows optimal path.\n"
      "  Green section = safe to go fast. Orange = lift throttle. Red = brake hard.\n"
      "  Wide entry > apex > wide exit for corners (classic racing line).\n"
      "\nWINNING STRATEGY:\n"
      "  Stay on tarmac unless doing cross-country. \n"
      "  Never brake when wheels are turned (understeer risk). \n"
      "  Use Rewind liberally after any collision. \n"
      "  In drift zones, initiate early with handbrake, maintain angle with throttle+countersteer."
  ),

  "situation_list": ["RACING", "DRIFT", "STUNT", "OFFROAD", "STUCK", "MENU"],

  # ── LEGACY BEHAVIORS (situation → tracks; kept for compatibility) ──────────
  "behaviors": {
    "RACING":  [[ {"keys": ["w"], "hold_ms": 1500} ]],
    "DRIFT":   [[ {"keys": ["space", "a"], "hold_ms": 300} ]],
    "STUNT":   [[ {"keys": ["w"], "hold_ms": 2000} ]],
    "OFFROAD": [[ {"keys": ["w"], "hold_ms": 1200} ]],
    "STUCK":   [[ {"keys": ["r"], "hold_ms": 120} ]],
    "MENU":    []
  },

  # ── NAMED ACTIONS ─────────────────────────────────────────────────────────
  "named_actions": {

    # ── STRAIGHT-LINE ACCELERATION ───────────────────────────────────────────
    "FULL_THROTTLE":          [{"keys": ["w"],           "hold_ms": 1800}],
    "THROTTLE_MEDIUM":        [{"keys": ["w"],           "hold_ms": 900}],
    "THROTTLE_LIGHT":         [{"keys": ["w"],           "hold_ms": 400}],

    # ── LEFT CURVES / CORNERS ────────────────────────────────────────────────
    "ACCEL_LEFT_GENTLE":      [{"keys": ["w", "a"],      "hold_ms": 800}],
    "ACCEL_LEFT_MEDIUM":      [{"keys": ["w", "a"],      "hold_ms": 550}],
    "ACCEL_LEFT_TIGHT":       [{"keys": ["w", "a"],      "hold_ms": 350}],
    "COAST_LEFT":             [{"keys": ["a"],            "hold_ms": 500}],

    # ── RIGHT CURVES / CORNERS ───────────────────────────────────────────────
    "ACCEL_RIGHT_GENTLE":     [{"keys": ["w", "d"],      "hold_ms": 800}],
    "ACCEL_RIGHT_MEDIUM":     [{"keys": ["w", "d"],      "hold_ms": 550}],
    "ACCEL_RIGHT_TIGHT":      [{"keys": ["w", "d"],      "hold_ms": 350}],
    "COAST_RIGHT":            [{"keys": ["d"],            "hold_ms": 500}],

    # ── BRAKING ──────────────────────────────────────────────────────────────
    "BRAKE_STRAIGHT":         [{"keys": ["s"],            "hold_ms": 500}],
    "BRAKE_STEER_LEFT":       [{"keys": ["s", "a"],       "hold_ms": 600}],
    "BRAKE_STEER_RIGHT":      [{"keys": ["s", "d"],       "hold_ms": 600}],
    "EMERGENCY_BRAKE":        [{"keys": ["s", "space"],   "hold_ms": 500}],

    # ── CORNER: BRAKE THEN ACCELERATE OUT (sequential) ───────────────────────
    "CORNER_BRAKE_EXIT_LEFT": [{"sequence": [
        {"keys": ["s"],           "hold_ms": 450, "delay_after_ms": 80},
        {"keys": ["w", "a"],      "hold_ms": 700}
    ]}],
    "CORNER_BRAKE_EXIT_RIGHT":[{"sequence": [
        {"keys": ["s"],           "hold_ms": 450, "delay_after_ms": 80},
        {"keys": ["w", "d"],      "hold_ms": 700}
    ]}],

    # ── REVERSE ──────────────────────────────────────────────────────────────
    "REVERSE":                [{"keys": ["s"],            "hold_ms": 1200}],
    "REVERSE_LEFT":           [{"keys": ["s", "a"],       "hold_ms": 900}],
    "REVERSE_RIGHT":          [{"keys": ["s", "d"],       "hold_ms": 900}],

    # ── HANDBRAKE / DRIFT INITIATION ─────────────────────────────────────────
    "HANDBRAKE_LEFT":         [{"keys": ["space", "a"],   "hold_ms": 350}],
    "HANDBRAKE_RIGHT":        [{"keys": ["space", "d"],   "hold_ms": 350}],

    # ── DRIFT MAINTENANCE (throttle + countersteer) ───────────────────────────
    # Drifting LEFT (car slides left, countersteer = steer right = D)
    "DRIFT_MAINTAIN_LEFT":    [{"keys": ["w", "d"],       "hold_ms": 700}],
    # Drifting RIGHT (car slides right, countersteer = steer left = A)
    "DRIFT_MAINTAIN_RIGHT":   [{"keys": ["w", "a"],       "hold_ms": 700}],

    # ── DRIFT COMBOS (initiate then maintain -- sequential) ───────────────────
    "DRIFT_COMBO_LEFT": [{"sequence": [
        {"keys": ["space", "a"], "hold_ms": 300, "delay_after_ms": 80},
        {"keys": ["w", "d"],     "hold_ms": 900}
    ]}],
    "DRIFT_COMBO_RIGHT": [{"sequence": [
        {"keys": ["space", "d"], "hold_ms": 300, "delay_after_ms": 80},
        {"keys": ["w", "a"],     "hold_ms": 900}
    ]}],

    # ── SPIN RECOVERY (countersteer to correct a spin) ────────────────────────
    # Car spun left (nose pointing left) -- steer right + throttle to recover
    "SPIN_RECOVER_LEFT":      [{"keys": ["w", "d"],       "hold_ms": 600}],
    # Car spun right (nose pointing right) -- steer left + throttle to recover
    "SPIN_RECOVER_RIGHT":     [{"keys": ["w", "a"],       "hold_ms": 600}],

    # ── GEAR SHIFTING (manual gearbox only) ───────────────────────────────────
    "SHIFT_UP":               [{"keys": ["e"],            "hold_ms": 80}],
    "SHIFT_DOWN":             [{"keys": ["q"],            "hold_ms": 80}],
    "SHIFT_UP_ACCELERATE": [{"sequence": [
        {"keys": ["e"],           "hold_ms": 80,  "delay_after_ms": 60},
        {"keys": ["w"],           "hold_ms": 1200}
    ]}],

    # ── DRAG RACE (max launch, optimal shifts) ───────────────────────────────
    "DRAG_LAUNCH":            [{"keys": ["w", "shift"],   "hold_ms": 500}],
    "DRAG_FULL_THROTTLE":     [{"keys": ["w"],            "hold_ms": 2500}],

    # ── PR STUNTS ────────────────────────────────────────────────────────────
    # Speed Trap / Speed Zone: straighten up and hold full throttle
    "SPEED_TRAP_BLAST":       [{"keys": ["w"],            "hold_ms": 3000}],
    # Danger Sign / Jump: approach at maximum speed
    "JUMP_APPROACH":          [{"keys": ["w"],            "hold_ms": 3000}],
    # Drift Zone: combo initiation based on zone curve direction
    "DRIFT_ZONE_LEFT":  [{"sequence": [
        {"keys": ["space", "a"], "hold_ms": 320, "delay_after_ms": 80},
        {"keys": ["w", "d"],     "hold_ms": 1000}
    ]}],
    "DRIFT_ZONE_RIGHT": [{"sequence": [
        {"keys": ["space", "d"], "hold_ms": 320, "delay_after_ms": 80},
        {"keys": ["w", "a"],     "hold_ms": 1000}
    ]}],

    # ── OVERTAKING ────────────────────────────────────────────────────────────
    # Pull left then overtake
    "OVERTAKE_LEFT": [{"sequence": [
        {"keys": ["a"],           "hold_ms": 300, "delay_after_ms": 60},
        {"keys": ["w"],           "hold_ms": 1500},
        {"keys": ["d"],           "hold_ms": 250}
    ]}],
    # Pull right then overtake
    "OVERTAKE_RIGHT": [{"sequence": [
        {"keys": ["d"],           "hold_ms": 300, "delay_after_ms": 60},
        {"keys": ["w"],           "hold_ms": 1500},
        {"keys": ["a"],           "hold_ms": 250}
    ]}],

    # ── TRAFFIC / OBSTACLE AVOIDANCE ─────────────────────────────────────────
    "SWERVE_LEFT":            [{"keys": ["a"],            "hold_ms": 250}],
    "SWERVE_RIGHT":           [{"keys": ["d"],            "hold_ms": 250}],
    "SWERVE_LEFT_FULL": [{"sequence": [
        {"keys": ["s"],           "hold_ms": 200, "delay_after_ms": 50},
        {"keys": ["a"],           "hold_ms": 350}
    ]}],
    "SWERVE_RIGHT_FULL": [{"sequence": [
        {"keys": ["s"],           "hold_ms": 200, "delay_after_ms": 50},
        {"keys": ["d"],           "hold_ms": 350}
    ]}],

    # ── OFF-ROAD DRIVING ─────────────────────────────────────────────────────
    "OFFROAD_THROTTLE":       [{"keys": ["w"],            "hold_ms": 1200}],
    "OFFROAD_LEFT":           [{"keys": ["w", "a"],       "hold_ms": 600}],
    "OFFROAD_RIGHT":          [{"keys": ["w", "d"],       "hold_ms": 600}],
    "OFFROAD_CAREFUL":        [{"keys": ["w"],            "hold_ms": 600}],

    # ── CRASH RECOVERY ────────────────────────────────────────────────────────
    "REWIND":                 [{"keys": ["r"],            "hold_ms": 120}],
    "REWIND_HOLD":            [{"keys": ["r"],            "hold_ms": 600}],
    "UNSTICK_REVERSE":        [{"keys": ["s"],            "hold_ms": 1000}],
    "UNSTICK_REVERSE_LEFT":   [{"keys": ["s", "a"],       "hold_ms": 700}],
    "UNSTICK_REVERSE_RIGHT":  [{"keys": ["s", "d"],       "hold_ms": 700}],

    # ── CAMERA / LOOK ─────────────────────────────────────────────────────────
    "LOOK_LEFT":              [{"keys": ["left"],         "hold_ms": 300}],
    "LOOK_RIGHT":             [{"keys": ["right"],        "hold_ms": 300}],
    "LOOK_BACK":              [{"keys": ["down"],         "hold_ms": 400}],
    "LOOK_FORWARD":           [{"keys": ["up"],           "hold_ms": 300}],
    "SWITCH_CAMERA":          [{"keys": ["tab"],          "hold_ms": 100}],

    # ── UI / INTERFACE ────────────────────────────────────────────────────────
    "ACTIVATE":               [{"keys": ["enter"],        "hold_ms": 100}],
    "HORN":                   [{"keys": ["h"],            "hold_ms": 200}],

    # ── DO NOTHING ────────────────────────────────────────────────────────────
    "DO_NOTHING": []
  },

  # ── NAMED ACTION DESCRIPTIONS (fed to LLM) ────────────────────────────────
  "named_action_descriptions": {
    "FULL_THROTTLE":          "Hold W 1.8s -- maximum sustained acceleration. Use on long straight roads with no corners ahead.",
    "THROTTLE_MEDIUM":        "Hold W 0.9s -- moderate acceleration. Use approaching a corner or in traffic.",
    "THROTTLE_LIGHT":         "Hold W 0.4s -- brief pulse of throttle. Use on slippery surface or when exiting a corner slowly.",

    "ACCEL_LEFT_GENTLE":      "W+A 0.8s -- accelerate and steer left gently. Use for a wide sweeping left curve.",
    "ACCEL_LEFT_MEDIUM":      "W+A 0.55s -- accelerate and steer left at medium clip. Use for a standard left corner.",
    "ACCEL_LEFT_TIGHT":       "W+A 0.35s -- accelerate and steer left with short input. Use for a tight left turn (sacrifice some speed).",
    "COAST_LEFT":             "A only 0.5s -- steer left without throttle/brake. Use when coasting around a gentle left curve.",

    "ACCEL_RIGHT_GENTLE":     "W+D 0.8s -- accelerate and steer right gently. Use for a wide sweeping right curve.",
    "ACCEL_RIGHT_MEDIUM":     "W+D 0.55s -- accelerate and steer right at medium clip. Use for a standard right corner.",
    "ACCEL_RIGHT_TIGHT":      "W+D 0.35s -- accelerate and steer right with short input. Use for a tight right turn.",
    "COAST_RIGHT":            "D only 0.5s -- steer right without throttle/brake. Use when coasting around a gentle right curve.",

    "BRAKE_STRAIGHT":         "S 0.5s -- brake in a straight line. Use when approaching a very tight corner or obstacle at speed.",
    "BRAKE_STEER_LEFT":       "S+A 0.6s -- brake and steer left simultaneously. Use when turning left while decelerating hard.",
    "BRAKE_STEER_RIGHT":      "S+D 0.6s -- brake and steer right simultaneously. Use when turning right while decelerating hard.",
    "EMERGENCY_BRAKE":        "S+Space 0.5s -- combined brake and handbrake for instant stop. Use to avoid an imminent collision.",

    "CORNER_BRAKE_EXIT_LEFT": "S 450ms then W+A 700ms -- brake into corner then accelerate out left. Use for a proper left hairpin or tight corner.",
    "CORNER_BRAKE_EXIT_RIGHT":"S 450ms then W+D 700ms -- brake into corner then accelerate out right. Use for a proper right hairpin or tight corner.",

    "REVERSE":                "S 1.2s -- reverse straight back. Use when stuck against a wall facing forward.",
    "REVERSE_LEFT":           "S+A 0.9s -- reverse and turn left (backs car to the right). Use to reorient after a wall hit on right side.",
    "REVERSE_RIGHT":          "S+D 0.9s -- reverse and turn right (backs car to the left). Use to reorient after a wall hit on left side.",

    "HANDBRAKE_LEFT":         "Space+A 0.35s -- handbrake turn to the left. Use to initiate drift or make a U-turn left.",
    "HANDBRAKE_RIGHT":        "Space+D 0.35s -- handbrake turn to the right. Use to initiate drift or make a U-turn right.",

    "DRIFT_MAINTAIN_LEFT":    "W+D 0.7s (countersteer) -- throttle + right steer while drifting left. Use to sustain an existing left drift.",
    "DRIFT_MAINTAIN_RIGHT":   "W+A 0.7s (countersteer) -- throttle + left steer while drifting right. Use to sustain an existing right drift.",

    "DRIFT_COMBO_LEFT":       "Space+A 300ms then W+D 900ms -- initiate drift left then maintain with countersteer. Use at start of a left drift zone or tight left.",
    "DRIFT_COMBO_RIGHT":      "Space+D 300ms then W+A 900ms -- initiate drift right then maintain with countersteer. Use at start of a right drift zone or tight right.",

    "SPIN_RECOVER_LEFT":      "W+D 0.6s -- full throttle + right steer to correct a leftward spin. Use when car is spinning/oversteering to the left.",
    "SPIN_RECOVER_RIGHT":     "W+A 0.6s -- full throttle + left steer to correct a rightward spin. Use when car is spinning/oversteering to the right.",

    "SHIFT_UP":               "E 80ms -- shift up one gear. Use when RPM is redlining (needle at right end of rev counter).",
    "SHIFT_DOWN":             "Q 80ms -- shift down one gear. Use before braking into a corner or when engine is lugging.",
    "SHIFT_UP_ACCELERATE":    "E then W -- shift up then hold full throttle. Use in a drag race or when engine hits redline on a straight.",

    "DRAG_LAUNCH":            "W+Shift 0.5s -- clutch-kick launch start. Use at the very beginning of a drag race.",
    "DRAG_FULL_THROTTLE":     "W 2.5s -- full throttle blast for drag race. Use on the drag strip straight.",

    "SPEED_TRAP_BLAST":       "W 3s -- maximum sustained throttle. Use when the SPEED TRAP icon is visible on a straight section (blue lightning bolt).",
    "JUMP_APPROACH":          "W 3s -- maximum throttle approaching a ramp. Use when a DANGER SIGN jump ramp is directly ahead (skull icon).",
    "DRIFT_ZONE_LEFT":        "Space+A then W+D -- full left drift zone combo. Use when entering a DRIFT ZONE that curves to the left (orange S-arrows).",
    "DRIFT_ZONE_RIGHT":       "Space+D then W+A -- full right drift zone combo. Use when entering a DRIFT ZONE that curves to the right (orange S-arrows).",

    "OVERTAKE_LEFT":          "Swerve left then blast then tuck right -- overtake an opponent by pulling left, accelerating past, tucking back in.",
    "OVERTAKE_RIGHT":         "Swerve right then blast then tuck left -- overtake an opponent by pulling right, accelerating past, tucking back in.",

    "SWERVE_LEFT":            "A 0.25s -- quick steer left. Use to dodge an obstacle, traffic car, or wall corner on the right.",
    "SWERVE_RIGHT":           "D 0.25s -- quick steer right. Use to dodge an obstacle, traffic car, or wall corner on the left.",
    "SWERVE_LEFT_FULL":       "Light brake then hard left -- brake and swerve left fully. Use for imminent collision with car/barrier on the right.",
    "SWERVE_RIGHT_FULL":      "Light brake then hard right -- brake and swerve right fully. Use for imminent collision with car/barrier on the left.",

    "OFFROAD_THROTTLE":       "W 1.2s -- steady throttle for off-road. Use on dirt, gravel, or grass with no major obstacles ahead.",
    "OFFROAD_LEFT":           "W+A 0.6s -- throttle and steer left off-road. Use to navigate around rocks or trees to the right.",
    "OFFROAD_RIGHT":          "W+D 0.6s -- throttle and steer right off-road. Use to navigate around rocks or trees to the left.",
    "OFFROAD_CAREFUL":        "W 0.6s -- short throttle bursts off-road. Use on very rough terrain, rivers, or steep slopes.",

    "REWIND":                 "R 120ms -- tap Rewind. Use immediately after a crash, wall hit, spin, or going off course.",
    "REWIND_HOLD":            "R 600ms -- hold Rewind to go further back in time. Use after a multi-car pile-up or off a cliff.",
    "UNSTICK_REVERSE":        "S 1s -- reverse out of stuck position. Use when car is wedged in terrain or against a wall.",
    "UNSTICK_REVERSE_LEFT":   "S+A 0.7s -- reverse and turn left to free car. Use when stuck with open space on the left.",
    "UNSTICK_REVERSE_RIGHT":  "S+D 0.7s -- reverse and turn right to free car. Use when stuck with open space on the right.",

    "LOOK_LEFT":              "Left arrow 0.3s -- look left. Use to check for opponents coming from the left or see a left junction.",
    "LOOK_RIGHT":             "Right arrow 0.3s -- look right. Use to check for opponents on the right or see a right junction.",
    "LOOK_BACK":              "Down arrow 0.4s -- look back. Use to check the gap to the car behind while racing.",
    "LOOK_FORWARD":           "Up arrow 0.3s -- reset view forward. Use after looking around to restore the driving view.",
    "SWITCH_CAMERA":          "Tab -- change camera view. Use if current view is obstructed or you need a different perspective.",

    "ACTIVATE":               "Enter -- accept/confirm. Use ONLY when an on-screen button press prompt (Enter/Accept) is visible.",
    "HORN":                   "H -- sound horn. No tactical use but can be used as a celebration or warning.",

    "DO_NOTHING":             "No input. Use ONLY during loading screens, cutscenes, reward screens, or any time the car cannot be controlled."
  },

  # ── DECISION RULES ────────────────────────────────────────────────────────
  "decision_rules": [
    "RULE 1 -- MENU / LOADING / CUTSCENE [highest override]:",
    "  Loading bar visible, black screen transition, cutscene playing,",
    "  reward/XP screen, menu open, or race results showing",
    "  => DO_NOTHING",
    "",
    "RULE 2 -- CRASH / SPIN / WRONG DIRECTION [second override]:",
    "  Car has collided hard (airbag animation, crash sound cue visible in replay),",
    "  car is facing more than ~90 degrees from the intended direction,",
    "  car has stopped or is stationary in the middle of a race,",
    "  or the car has fallen off the road / off a cliff",
    "  => REWIND  (always prefer Rewind over trying to drive out of a bad position)",
    "  If Rewind was picked but car appears stuck against same obstacle next frame:",
    "  => REWIND_HOLD  (hold R longer to go further back)",
    "",
    "RULE 3 -- STUCK IN TERRAIN / AGAINST WALL:",
    "  Car is moving very slowly or not at all despite W being pressed,",
    "  wheels are in the air, car is beached on rocks, or same wall fills the view repeatedly",
    "  => REWIND  (preferred -- fastest recovery)",
    "  If Rewind is unavailable or cooldown active (rewind icon greyed out):",
    "    Clear space behind on the LEFT:",
    "    => UNSTICK_REVERSE_LEFT",
    "    Clear space behind on the RIGHT:",
    "    => UNSTICK_REVERSE_RIGHT",
    "    No clear space -- reverse straight:",
    "    => UNSTICK_REVERSE",
    "",
    "RULE 4 -- PR STUNT: SPEED TRAP (blue lightning bolt icon visible on or near the road):",
    "  Speed trap camera is directly ahead on a straight section",
    "  Road is straight and free of obstacles between you and the camera",
    "  => SPEED_TRAP_BLAST  (maximum sustained throttle to cross at peak speed)",
    "  Speed trap ahead but road curves to the LEFT into it:",
    "  => ACCEL_LEFT_GENTLE  (don't sacrifice speed, just gently track the road)",
    "  Speed trap ahead but road curves to the RIGHT into it:",
    "  => ACCEL_RIGHT_GENTLE",
    "",
    "RULE 5 -- PR STUNT: DANGER SIGN / JUMP RAMP (skull icon or obvious ramp ahead):",
    "  Ramp is directly ahead",
    "  => JUMP_APPROACH  (maximum throttle -- never brake before a jump)",
    "  Ramp is ahead but you are slightly left of it:",
    "  => ACCEL_RIGHT_GENTLE  (gently steer to line up, maintain speed)",
    "  Ramp is ahead but you are slightly right of it:",
    "  => ACCEL_LEFT_GENTLE",
    "",
    "RULE 6 -- PR STUNT: DRIFT ZONE (orange S-curve arrows / drift score counter visible):",
    "  Entering or inside a drift zone, zone curves primarily to the LEFT:",
    "  => DRIFT_ZONE_LEFT",
    "  Entering or inside a drift zone, zone curves primarily to the RIGHT:",
    "  => DRIFT_ZONE_RIGHT",
    "  Already drifting (sideways angle, smoke visible) -- car sliding LEFT (nose pointing left):",
    "  => DRIFT_MAINTAIN_LEFT  (countersteer right + throttle)",
    "  Already drifting -- car sliding RIGHT (nose pointing right):",
    "  => DRIFT_MAINTAIN_RIGHT  (countersteer left + throttle)",
    "",
    "RULE 7 -- DRAG RACE (drag strip, christmas tree / launch line visible):",
    "  Race has not started yet (countdown lights):",
    "  => DO_NOTHING  (wait for green light)",
    "  Green light shows / race just started:",
    "  => DRAG_LAUNCH",
    "  On the drag strip, no corners:",
    "  => DRAG_FULL_THROTTLE",
    "  RPM gauge redlining (needle far right) -- manual gearbox:",
    "  => SHIFT_UP_ACCELERATE",
    "",
    "RULE 8 -- IMMINENT COLLISION (car/barrier/wall VERY close, about to hit):",
    "  Object directly ahead with no time to steer -- impossible to avoid:",
    "  => EMERGENCY_BRAKE  (S+Space)",
    "  Object ahead, open space clearly on the LEFT:",
    "  => SWERVE_LEFT_FULL",
    "  Object ahead, open space clearly on the RIGHT:",
    "  => SWERVE_RIGHT_FULL",
    "",
    "RULE 9 -- OPPONENT CAR DIRECTLY AHEAD (racing -- car blocking your path):",
    "  Opponent car is right in front, open space on the LEFT side:",
    "  => OVERTAKE_LEFT",
    "  Opponent car is right in front, open space on the RIGHT side:",
    "  => OVERTAKE_RIGHT",
    "  Opponent car is directly ahead, no space to pass yet -- sit in slipstream:",
    "  => FULL_THROTTLE  (stay close to build slipstream boost, wait for a gap)",
    "",
    "RULE 10 -- CORNER AHEAD (road curves -- apply the correct corner technique):",
    "  ASSESS CORNER SEVERITY:",
    "    - Wide sweeping curve (road curves just slightly, plenty of road visible ahead): GENTLE",
    "    - Standard corner (road clearly turns, roughly 45-90 degrees): MEDIUM",
    "    - Tight corner or hairpin (road turns 90+ degrees, very little exit visible): TIGHT",
    "    - Very tight hairpin or U-turn: BRAKE-THEN-STEER",
    "",
    "  GENTLE LEFT curve ahead:",
    "  => ACCEL_LEFT_GENTLE",
    "  MEDIUM LEFT corner ahead, enough speed to use braking line:",
    "  => ACCEL_LEFT_MEDIUM",
    "  TIGHT LEFT corner -- reduce speed first:",
    "  => CORNER_BRAKE_EXIT_LEFT",
    "  HAIRPIN LEFT (very tight, must slow significantly):",
    "  => BRAKE_STEER_LEFT  then  ACCEL_LEFT_TIGHT  on the exit",
    "",
    "  GENTLE RIGHT curve ahead:",
    "  => ACCEL_RIGHT_GENTLE",
    "  MEDIUM RIGHT corner:",
    "  => ACCEL_RIGHT_MEDIUM",
    "  TIGHT RIGHT corner:",
    "  => CORNER_BRAKE_EXIT_RIGHT",
    "  HAIRPIN RIGHT:",
    "  => BRAKE_STEER_RIGHT  then  ACCEL_RIGHT_TIGHT",
    "",
    "  The racing line colour helps assess: GREEN=gas, ORANGE=lift, RED=brake.",
    "  Wide entry, clip apex, wide exit -- stay on tarmac.",
    "",
    "RULE 11 -- SPIN DETECTED (car has rotated sideways, not a controlled drift):",
    "  Car nose has swung LEFT (car spinning counterclockwise), you feel oversteer left:",
    "  => SPIN_RECOVER_LEFT  (W+D -- countersteer right + throttle)",
    "  Car nose has swung RIGHT (car spinning clockwise), oversteer right:",
    "  => SPIN_RECOVER_RIGHT  (W+A -- countersteer left + throttle)",
    "",
    "RULE 12 -- GEAR CHANGE (manual gearbox only -- if telemetry / gear indicator visible):",
    "  RPM gauge at red-line, gear indicator shows can upshift:",
    "  => SHIFT_UP",
    "  Engine lugging at low RPM (coming out of a corner):",
    "  => SHIFT_DOWN",
    "",
    "RULE 13 -- OFF-ROAD / CROSS COUNTRY (dirt, grass, gravel, river, rocks):",
    "  No asphalt under the car, cross-country checkpoint ahead, terrain is rough",
    "  No major obstacles immediately ahead:",
    "  => OFFROAD_THROTTLE",
    "  Obstacle (rock, tree, fence) on the RIGHT -- go left:",
    "  => OFFROAD_LEFT",
    "  Obstacle on the LEFT -- go right:",
    "  => OFFROAD_RIGHT",
    "  Very rough terrain, steep slope, river crossing -- go easy:",
    "  => OFFROAD_CAREFUL",
    "",
    "RULE 14 -- TRAFFIC AHEAD IN FREEROAM (civilian car or truck in your lane):",
    "  Civilian car ahead, space on the LEFT to pass:",
    "  => SWERVE_LEFT",
    "  Civilian car ahead, space on the RIGHT to pass:",
    "  => SWERVE_RIGHT",
    "",
    "RULE 15 -- STRAIGHT ROAD (default -- clear asphalt ahead, no corners):",
    "  Long straight road, no obstacles, no corners visible yet:",
    "  => FULL_THROTTLE",
    "  Approaching the end of a straight where a corner will appear:",
    "  => THROTTLE_MEDIUM  (prepare to brake / steer)",
    "  Exiting a corner onto a short straight before the next bend:",
    "  => THROTTLE_LIGHT  (build speed carefully)",
  ],

  # ── CRITICAL CONSTRAINTS ──────────────────────────────────────────────────
  "constraints": [
    "* ALWAYS use Rewind (R) after a crash, spin, or going off course -- it is the fastest recovery.",
    "* NEVER brake while wheels are fully turned (understeer risk) -- straighten briefly before braking.",
    "* NEVER pick DO_NOTHING if the car is moving or a race is active.",
    "* NEVER pick ACTIVATE unless an on-screen Enter/Accept prompt is literally visible.",
    "* NEVER pick JUMP_APPROACH unless a physical jump ramp is right in front of you.",
    "* NEVER pick SPEED_TRAP_BLAST on a curved road -- straighten up first or you will crash.",
    "* NEVER use DRIFT_COMBO on a straight road at very high speed -- dangerous spin risk.",
    "* NEVER use EMERGENCY_BRAKE unless a collision is truly unavoidable in the next second.",
    "* If the same action was chosen 3+ times in a row and the car position has not changed, switch to REWIND.",
    "* In a corner, always prefer a CORNER sequence (brake-then-exit) over pure braking alone.",
    "* On asphalt with a clean racing line: smooth inputs > aggressive inputs. Quality lap times beat aggressive spins.",
  ],

  # ── SITUATION CHECKLIST (shown in the user turn alongside every screenshot) ─
  "situation_checklist": [
    "Examine the screenshot carefully and answer these questions in order:",
    "  1.  Is a loading screen, menu, cutscene, or results screen visible?          -> RULE 1  (DO_NOTHING)",
    "  2.  Has the car crashed, spun out, or is it facing the wrong direction?       -> RULE 2  (REWIND)",
    "  3.  Is the car stuck against a wall or in terrain (stuck/not moving)?         -> RULE 3  (REWIND/UNSTICK)",
    "  4.  Is a SPEED TRAP lightning bolt icon visible on a straight road ahead?     -> RULE 4  (SPEED_TRAP_BLAST)",
    "  5.  Is a DANGER SIGN jump ramp directly in front of the car?                  -> RULE 5  (JUMP_APPROACH)",
    "  6.  Are orange DRIFT ZONE arrows or a drift score counter visible?             -> RULE 6  (DRIFT_ZONE_*)",
    "  7.  Is this a DRAG RACE strip (no corners, christmas tree)?                   -> RULE 7  (DRAG_*)",
    "  8.  Is a collision with a wall/barrier/car less than 1 second away?           -> RULE 8  (EMERGENCY_BRAKE/SWERVE)",
    "  9.  Is an opponent car directly blocking your racing line?                    -> RULE 9  (OVERTAKE_*)",
    "  10. Is there a corner or curve ahead on the road?                             -> RULE 10 (corner actions)",
    "  11. Is the car visibly spinning out of control (not a drift)?                 -> RULE 11 (SPIN_RECOVER_*)",
    "  12. Is the car on dirt/grass/gravel (off-road terrain)?                       -> RULE 13 (OFFROAD_*)",
    "  13. Is there a civilian car or slow vehicle ahead in freeroam?                -> RULE 14 (SWERVE_*)",
    "  14. Is the road ahead clear, straight asphalt with no obstacles?              -> RULE 15 (FULL_THROTTLE)",
    "Output EXACTLY ONE action name from the list above."
  ],

  # ── LEGACY ACTION LIST + KEY MAP ─────────────────────────────────────────
  "action_list": [
    "ACCELERATE", "BRAKE", "STEER_LEFT", "STEER_RIGHT",
    "SHIFT_UP", "SHIFT_DOWN", "CLUTCH", "EBRAKE",
    "REWIND", "ACTIVATE", "SWITCH_CAMERA", "HORN", "MAP",
    "LOOK_LEFT", "LOOK_RIGHT", "LOOK_BACK", "LOOK_FORWARD",
    "RADIO_NEXT", "RADIO_PREV", "PHOTO_MODE", "TELEMETRY",
    "TOGGLE_LEADERBOARD", "IDLE"
  ],

  "key_map": {
    "ACCELERATE":        {"type": "keyboard", "key": "w"},
    "BRAKE":             {"type": "keyboard", "key": "s"},
    "STEER_LEFT":        {"type": "keyboard", "key": "a"},
    "STEER_RIGHT":       {"type": "keyboard", "key": "d"},
    "SHIFT_UP":          {"type": "keyboard", "key": "e"},
    "SHIFT_DOWN":        {"type": "keyboard", "key": "q"},
    "CLUTCH":            {"type": "keyboard", "key": "shift"},
    "EBRAKE":            {"type": "keyboard", "key": "space"},
    "REWIND":            {"type": "keyboard", "key": "r"},
    "ACTIVATE":          {"type": "keyboard", "key": "enter"},
    "SWITCH_CAMERA":     {"type": "keyboard", "key": "tab"},
    "HORN":              {"type": "keyboard", "key": "h"},
    "MAP":               {"type": "keyboard", "key": "m"},
    "LOOK_LEFT":         {"type": "keyboard", "key": "left"},
    "LOOK_RIGHT":        {"type": "keyboard", "key": "right"},
    "LOOK_BACK":         {"type": "keyboard", "key": "down"},
    "LOOK_FORWARD":      {"type": "keyboard", "key": "up"},
    "RADIO_NEXT":        {"type": "keyboard", "key": "="},
    "RADIO_PREV":        {"type": "keyboard", "key": "-"},
    "PHOTO_MODE":        {"type": "keyboard", "key": "p"},
    "TELEMETRY":         {"type": "keyboard", "key": "t"},
    "TOGGLE_LEADERBOARD":{"type": "keyboard", "key": "l"},
    "IDLE": None
  },

  "action_descriptions": {
    "ACCELERATE":  "Hold W to accelerate",
    "BRAKE":       "Hold S to brake/reverse",
    "STEER_LEFT":  "Hold A to steer left",
    "STEER_RIGHT": "Hold D to steer right",
    "IDLE":        "No input -- cutscene/menu"
  }
}

out = pathlib.Path("games_config/forza_horizon_5/config.json")
out.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

n_actions = len(cfg["named_actions"])
n_rules   = len(cfg["decision_rules"])
n_cons    = len(cfg["constraints"])
n_chk     = len(cfg["situation_checklist"])

print(f"config.json written  ({out.stat().st_size:,} bytes)")
print(f"  named_actions       : {n_actions}")
print(f"  decision_rules      : {n_rules} lines")
print(f"  constraints         : {n_cons} items")
print(f"  situation_checklist : {n_chk} items")
