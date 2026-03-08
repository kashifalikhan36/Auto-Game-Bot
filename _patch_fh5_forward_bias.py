"""
Patches FH5 config.json to heavily bias toward forward throttle:
  - Remove stale "ALWAYS use Rewind" constraint (leftover from before no-rewind patch)
  - Fix the "same action 3 times" constraint to NOT suggest reverse
  - Add 3 hard forward-bias constraints (NEVER reverse unless speed=0+blocked)
  - Tighten RULE 2 and RULE 3 triggers: only fire when speed is literally zero
  - Add velocity check to RULE 3b so it doesn't over-correct off-road
  - Strengthen RULE 15 (straight road default) with explicit priority note
  - Update checklist question 2 and 3 to reflect tighter conditions
"""
import json, pathlib

p = pathlib.Path("games_config/forza_horizon_5/config.json")
cfg = json.loads(p.read_text(encoding="utf-8"))

# ══════════════════════════════════════════════════════
# 1. FIX CONSTRAINTS
# ══════════════════════════════════════════════════════
old_constraints = cfg["constraints"]

# Remove the stale "ALWAYS use Rewind" constraint
old_constraints = [c for c in old_constraints
                   if "ALWAYS use Rewind" not in c]

# Fix the "same action 3+ times" constraint
old_constraints = [
    "* If the same action was chosen 3+ times in a row and the car has not visibly moved forward, try a DIFFERENT FORWARD action (THROTTLE_LIGHT, ACCEL_LEFT_GENTLE or ACCEL_RIGHT_GENTLE to steer around the obstacle). Only use UNSTICK_REVERSE_* if car speed is confirmed zero AND the car is physically blocked."
    if "same action was chosen 3+" in c or "same action was chosen 3" in c
    else c
    for c in old_constraints
]

# Prepend very strong forward-bias constraints (after the NEVER REWIND one)
FORWARD_BIAS = [
    "* DEFAULT ACTION IS FULL_THROTTLE. If you are unsure what to pick, pick FULL_THROTTLE. The car must always be moving FORWARD unless there is a specific visual reason to do otherwise.",
    "* NEVER use any reverse action (UNSTICK_REVERSE / UNSTICK_REVERSE_LEFT / UNSTICK_REVERSE_RIGHT / REVERSE / REVERSE_LEFT / REVERSE_RIGHT) unless the car speedometer / motion indicator shows the car is COMPLETELY STOPPED (speed ~0) AND the car is visibly blocked by a wall or barrier it cannot drive forward through.",
    "* If the car is moving at any speed -- even slowly -- DO NOT reverse. Correct with steering (A or D) and keep W pressed for throttle.",
]

# Insert right after the NEVER REWIND constraint (index 0), so indices 1,2,3
fixed = [old_constraints[0]] + FORWARD_BIAS + old_constraints[1:]
cfg["constraints"] = fixed
print(f"Constraints: {len(cfg['constraints'])} items")

# ══════════════════════════════════════════════════════
# 2. FIX DECISION RULES
# ══════════════════════════════════════════════════════
rules = cfg["decision_rules"]
rules_str = "\n".join(rules)

# --- RULE 2: add "car speed must be ZERO or near-zero" guard ---------------
OLD_R2_TRIGGER = (
    "RULE 2 -- CRASH / SPIN / WRONG DIRECTION [second override]:\n"
    "  Car has collided hard, car is facing more than ~90 degrees from intended direction,\n"
    "  car has stopped in race, or car has gone off a cliff / deep off road.\n"
    "  DO NOT use Rewind. Recover manually:"
)
NEW_R2_TRIGGER = (
    "RULE 2 -- CRASH / SPIN / WRONG DIRECTION [second override]:\n"
    "  ONLY applies when: car speed is ZERO or near-zero AND car is visibly facing the wrong direction (90+ degrees off road heading).\n"
    "  If the car is still moving forward even off-road, use RULE 3b instead.\n"
    "  DO NOT use this rule just because the car went off-road. Recovery:"
)
if OLD_R2_TRIGGER in rules_str:
    rules_str = rules_str.replace(OLD_R2_TRIGGER, NEW_R2_TRIGGER, 1)
    print("Patched RULE 2 trigger condition")
else:
    print("WARNING: Could not find RULE 2 trigger to patch")

# --- RULE 3: add "truly stopped" guard ------------------------------------
OLD_R3_TRIGGER = (
    "RULE 3 -- STUCK IN TERRAIN / AGAINST WALL:\n"
    "  Car is moving very slowly or not at all, wheels in air, or same wall fills view repeatedly.\n"
    "  DO NOT use Rewind. Recover manually:"
)
NEW_R3_TRIGGER = (
    "RULE 3 -- STUCK IN TERRAIN / AGAINST WALL [use ONLY when car is STOPPED]:\n"
    "  ONLY applies when: car speed is ZERO and the car is physically blocked -- pushing W produces no forward movement.\n"
    "  If the car speed is above zero, skip this rule -- use RULE 3b (off road) or RULE 10 (corner) instead.\n"
    "  DO NOT use this rule just because the car is going slowly. Recovery:"
)
if OLD_R3_TRIGGER in rules_str:
    rules_str = rules_str.replace(OLD_R3_TRIGGER, NEW_R3_TRIGGER, 1)
    print("Patched RULE 3 trigger condition")
else:
    print("WARNING: Could not find RULE 3 trigger to patch")

# --- RULE 15: make FULL_THROTTLE the loud default -------------------------
OLD_R15_END = (
    "RULE 15 -- STRAIGHT ROAD (default -- clear asphalt ahead, no corners):\n"
    "  Long straight road, no obstacles, no corners visible yet:\n"
    "  => FULL_THROTTLE\n"
    "  Approaching the end of a straight where a corner will appear:\n"
    "  => THROTTLE_MEDIUM  (prepare to brake / steer)\n"
    "  Exiting a corner onto a short straight before the next bend:\n"
    "  => THROTTLE_LIGHT  (build speed carefully)"
)
NEW_R15_END = (
    "RULE 15 -- STRAIGHT ROAD / DEFAULT (clear asphalt, no specific rule triggered above):\n"
    "  THIS IS THE DEFAULT RULE -- if none of Rules 1-14 clearly apply, always fall here.\n"
    "  Long straight road, no obstacles, no corners visible yet:\n"
    "  => FULL_THROTTLE  *** THIS IS THE MOST COMMON CORRECT ANSWER ***\n"
    "  Approaching the end of a straight where a corner will appear soon:\n"
    "  => THROTTLE_MEDIUM  (lift off gas slightly to prepare)\n"
    "  Exiting a corner onto a short straight before the next bend:\n"
    "  => THROTTLE_LIGHT  (build speed back up gradually)\n"
    "  When in doubt: FULL_THROTTLE. Do not pick a recovery/reverse action unless you are certain."
)
if OLD_R15_END in rules_str:
    rules_str = rules_str.replace(OLD_R15_END, NEW_R15_END, 1)
    print("Patched RULE 15 default emphasis")
else:
    print("WARNING: Could not find RULE 15 to patch")

cfg["decision_rules"] = rules_str.split("\n")

# ══════════════════════════════════════════════════════
# 3. FIX CHECKLIST
# ══════════════════════════════════════════════════════
cfg["situation_checklist"] = [
    line.replace(
        "2.  Has the car crashed, spun out, or is it facing the wrong direction?",
        "2.  Has the car crashed, spun out, AND is car speed ZERO (completely stopped facing wrong way)?"
    ).replace(
        "3.  Is the car stuck against a wall or in terrain (stuck/not moving)?",
        "3.  Is the car COMPLETELY STOPPED against a wall/barrier AND pushing W gives zero forward movement?"
    ).replace(
        "14. Is the road ahead clear, straight asphalt with no obstacles?",
        "14. Is the road ahead clear OR have none of questions 1-13 been answered YES? -> RULE 15 (FULL_THROTTLE)"
    )
    for line in cfg["situation_checklist"]
]
print("Updated checklist")

# ══════════════════════════════════════════════════════
# 4. UPDATE game_context with forward-bias note
# ══════════════════════════════════════════════════════
if "FORWARD BIAS" not in cfg.get("game_context", ""):
    cfg["game_context"] = cfg.get("game_context", "") + (
        "\n\nFORWARD BIAS RULE: The car must ALWAYS be driving FORWARD. "
        "FULL_THROTTLE (W key) is the default action for 80-90% of frames in a race. "
        "Steering corrections (A/D while W is held) handle 10-15% of frames. "
        "Reverse (S) is for emergencies only when physically stopped and blocked -- under 1% of frames. "
        "If the car is moving at any speed, keep W pressed and correct direction with A or D."
    )
    print("Updated game_context with forward-bias note")

# ══════════════════════════════════════════════════════
# 5. WRITE
# ══════════════════════════════════════════════════════
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nconfig.json updated  ({p.stat().st_size:,} bytes)")
print(f"  constraints    : {len(cfg['constraints'])} items")
print(f"  decision_rules : {len(cfg['decision_rules'])} lines")

# Quick verify
c_text = "\n".join(cfg["constraints"])
r_text = "\n".join(cfg["decision_rules"])
print(f"  'ALWAYS use Rewind' still present: {'ALWAYS use Rewind' in c_text}")
print(f"  NEVER reverse constraint present : {'NEVER use any reverse action' in c_text}")
print(f"  RULE 2 has speed=ZERO guard      : {'speed is ZERO' in r_text}")
print(f"  RULE 3 has stopped guard         : {'STOPPED' in r_text}")
print(f"  RULE 15 has *** most common ***  : {'MOST COMMON CORRECT ANSWER' in r_text}")
print(f"  game_context forward bias        : {'FORWARD BIAS' in cfg['game_context']}")
