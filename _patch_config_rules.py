"""
Adds decision_rules, constraints, and situation_checklist to config.json.
Keeps all existing fields untouched.
"""
import json, pathlib

cfg_path = pathlib.Path(
    "games_config/metal_gear_5_the_phantom_pain/config.json"
)
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

# ── DECISION RULES ────────────────────────────────────────────────────────────
cfg["decision_rules"] = [
    "RULE 1 -- AMMO EMPTY [highest urgency for weapon]:",
    "  HUD ammo counter shows 0 or weapon is empty",
    "  => RELOAD_WEAPON",
    "",
    "RULE 2 -- ENEMY CLEARLY VISIBLE (enemy body on screen right now):",
    "  Enemy stationary or at close range",
    "  => AIM_BURST",
    "  Enemy moving or at medium range",
    "  => AIM_SHOOT",
    "  Enemy on your right -- sidestep left while firing",
    "  => AIM_SHOOT_STRAFE_LEFT",
    "  Enemy on your left -- sidestep right while firing",
    "  => AIM_SHOOT_STRAFE_RIGHT",
    "",
    "RULE 3 -- TAKING FIRE / COVER FIGHTING (enemy shooting at Snake):",
    "  Snake is being shot at and NOT yet in cover:",
    "  => STAY_IN_COVER  (press C immediately to crouch/prone behind cover)",
    "  Snake is crouched/prone in cover and enemy is still shooting:",
    "    Enemy close or stationary => COVER_BURST_COVER  (aim+3shots+crouch back)",
    "    Enemy far or moving       => PEEK_SHOOT_COVER   (aim+1shot+crouch back)",
    "  After shooting, enemy keeps firing -- stay low:",
    "  => STAY_IN_COVER",
    "  Health critically low while under fire:",
    "  => CROUCH_RUN_FORWARD  (crawl away to break line of sight)",
    "",
    "RULE 4 -- EMERGENCY DODGE (bullets/explosion VERY close, red screen flash):",
    "  => QUICK_DIVE",
    "  Then immediately:",
    "  => EVADE_RIGHT   OR   EVADE_LEFT   (sprint away from the source of fire)",
    "",
    "RULE 5 -- STUCK ON OBSTACLE / WALL (path blocked, same wall filling screen):",
    "  Step A: Try to vault over a low wall/fence/rock",
    "  => VAULT_OBSTACLE  (Shift+W+Space -- sprint and jump)",
    "  Step B: Still blocked -- open space visible on the RIGHT",
    "  => UNSTICK_SWING_RIGHT  (sweep camera right 150px then sprint)",
    "  Step B: Still blocked -- open space visible on the LEFT",
    "  => UNSTICK_SWING_LEFT   (sweep camera left 150px then sprint)",
    "  Step C: Completely stuck -- back up and reorient",
    "    Open route appears to be on the RIGHT after backing up",
    "  => BACK_AND_TURN_RIGHT  (S + camera right + W)",
    "    Open route appears to be on the LEFT after backing up",
    "  => BACK_AND_TURN_LEFT   (S + camera left + W)",
    "  Signs you are STUCK: wall/fence fills the frame, no progress after 2+ W presses.",
    "",
    "RULE 6 -- INTERACT PROMPT VISIBLE (E icon on screen):",
    "  An on-screen prompt with E key icon near object / door / NPC",
    "  => INTERACT",
    "",
    "RULE 7 -- YELLOW ALERT / STEALTH (enemy searching, not yet shooting):",
    "  Yellow ! or enemy patrol searching -- hide immediately",
    "  => CROUCH_TOGGLE  (press C to crouch/prone -- recovers health)",
    "  Need to peek at the situation without fully exposing Snake",
    "  => LOOK_RIGHT   OR   LOOK_LEFT   OR   LOOK_UP",
    "",
    "RULE 8 -- D-HORSE RIDING (currently ON horseback -- horse body/neck visible, riding HUD shown):",
    "  Road ahead is straight and clear",
    "  => HORSE_GALLOP_FORWARD",
    "  Road curves to the RIGHT",
    "  => HORSE_RIDE_RIGHT",
    "  Road curves to the LEFT",
    "  => HORSE_RIDE_LEFT",
    "  Approaching an enemy area or tight passage -- slow down",
    "  => HORSE_SLOW_STOP",
    "  Need to dismount (entering combat / tight area on foot)",
    "  => MOUNT_DISMOUNT_HORSE  (press E to get off)",
    "",
    "RULE 9 -- D-HORSE AVAILABLE NEARBY (horse standing close, not yet mounted):",
    "  D-Horse is visible on screen within reach",
    "  => MOUNT_DISMOUNT_HORSE  (press E to mount)",
    "",
    "RULE 10 -- CALL D-HORSE (on open road, no enemies nearby, no horse visible):",
    "  Snake is on an open road or wide flat area, safe, no horse in sight",
    "  => CALL_HORSE  (hold Q + press 2 to radio for D-Horse delivery)",
    "",
    "RULE 11 -- SCOUT UNKNOWN AREA (limited view, cannot see what is ahead):",
    "  Cannot see what is around a corner or over a ridge -- scan first",
    "  => USE_BINOCULARS  (hold F to scout and tag enemies safely)",
    "  OR pan the camera to see:",
    "  => LOOK_RIGHT   OR   LOOK_LEFT   OR   LOOK_UP",
    "",
    "RULE 12 -- EXPLORE / MOVE (default -- no immediate threats):",
    "  Clear path straight ahead, no enemies, no obstacles",
    "  => SPRINT_FORWARD",
    "  Path curves or you want to scan while running",
    "  => SPRINT_LOOK_RIGHT   OR   SPRINT_LOOK_LEFT   OR   SPRINT_LOOK_UP",
    "  Narrow passage or cautious movement needed",
    "  => RUN_FORWARD   OR   RUN_LOOK_RIGHT   OR   RUN_LOOK_LEFT",
    "  Need to step around something small",
    "  => STRAFE_LEFT   OR   STRAFE_RIGHT",
    "",
    "RULE 13 -- DO NOTHING [lowest priority]:",
    "  Cutscene playing / loading screen / in-game menu / dialogue box",
    "  => DO_NOTHING",
]

# ── CRITICAL CONSTRAINTS ──────────────────────────────────────────────────────
cfg["constraints"] = [
    "* NEVER pick DO_NOTHING if Snake can move freely on foot or horseback.",
    "* NEVER pick INTERACT unless the E prompt icon is literally visible on screen NOW.",
    "* NEVER pick AIM_SHOOT / AIM_BURST unless an enemy body is CLEARLY visible.",
    "* NEVER pick CALL_HORSE if already riding or if enemies are nearby.",
    "* NEVER stand still in the open with a clear path -- always move.",
    "* If you picked the same action 3+ times in a row and nothing changed, pick a different one from the same rule.",
]

# ── SITUATION CHECKLIST (shown in the user turn alongside each screenshot) ────
cfg["situation_checklist"] = [
    "Examine the screenshot carefully and answer these questions:",
    "  1. Is an enemy body clearly visible?                     -> RULE 2",
    "  2. Is Snake being shot at / under fire?                  -> RULE 3",
    "  3. Is there a wall/fence blocking the path directly ahead? -> RULE 5",
    "  4. Is Snake currently riding D-Horse (horse HUD visible)? -> RULE 8",
    "  5. Is D-Horse standing nearby (not yet mounted)?         -> RULE 9",
    "  6. Is the E interact prompt on screen?                   -> RULE 6",
    "  7. Is the ammo counter at 0?                             -> RULE 1",
    "  8. Is it a cutscene / menu / loading screen?             -> RULE 13",
    "  9. None of the above -- open path ahead                  -> RULE 12 (explore)",
    "Output ONE action name only.",
]

cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"config.json updated  ({cfg_path.stat().st_size} bytes)")
print(f"  decision_rules  : {len(cfg['decision_rules'])} lines")
print(f"  constraints     : {len(cfg['constraints'])} items")
print(f"  situation_checklist: {len(cfg['situation_checklist'])} items")
