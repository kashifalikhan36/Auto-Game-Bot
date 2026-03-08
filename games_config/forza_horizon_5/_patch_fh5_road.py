"""
Patches FH5 config.json to add road-return focus:
  - 6 new named actions (brake-realign-accelerate sequences)
  - New RULE 3b inserted between existing RULE 3 and RULE 4
  - Stronger constraints about staying on tarmac
  - Updated checklist question
"""
import json, pathlib

p = pathlib.Path("games_config/forza_horizon_5/config.json")
cfg = json.loads(p.read_text(encoding="utf-8"))

# ── 1. NEW NAMED ACTIONS ──────────────────────────────────────────────────────
# Insert them right before DO_NOTHING (the last key)

new_actions = {
    # Barely drifted off road – gentle nudge back while keeping light throttle
    "ROAD_NUDGE_LEFT": [{"sequence": [
        {"keys": ["a"],      "hold_ms": 300, "delay_after_ms": 60},
        {"keys": ["w"],      "hold_ms": 700}
    ]}],
    "ROAD_NUDGE_RIGHT": [{"sequence": [
        {"keys": ["d"],      "hold_ms": 300, "delay_after_ms": 60},
        {"keys": ["w"],      "hold_ms": 700}
    ]}],

    # Significantly off road (right side) – brake → steer left back → re-accelerate
    "ROAD_RETURN_LEFT": [{"sequence": [
        {"keys": ["s"],      "hold_ms": 500, "delay_after_ms": 100},
        {"keys": ["w", "a"], "hold_ms": 700, "delay_after_ms": 80},
        {"keys": ["w"],      "hold_ms": 900}
    ]}],
    # Significantly off road (left side) – brake → steer right back → re-accelerate
    "ROAD_RETURN_RIGHT": [{"sequence": [
        {"keys": ["s"],      "hold_ms": 500, "delay_after_ms": 100},
        {"keys": ["w", "d"], "hold_ms": 700, "delay_after_ms": 80},
        {"keys": ["w"],      "hold_ms": 900}
    ]}],

    # Hard off road (deep grass / hit a barrier) – hard brake → steer back → build speed
    "ROAD_RECOVER_LEFT": [{"sequence": [
        {"keys": ["s"],      "hold_ms": 700, "delay_after_ms": 120},
        {"keys": ["a"],      "hold_ms": 500, "delay_after_ms": 80},
        {"keys": ["w", "a"], "hold_ms": 600, "delay_after_ms": 60},
        {"keys": ["w"],      "hold_ms": 1200}
    ]}],
    "ROAD_RECOVER_RIGHT": [{"sequence": [
        {"keys": ["s"],      "hold_ms": 700, "delay_after_ms": 120},
        {"keys": ["d"],      "hold_ms": 500, "delay_after_ms": 80},
        {"keys": ["w", "d"], "hold_ms": 600, "delay_after_ms": 60},
        {"keys": ["w"],      "hold_ms": 1200}
    ]}],
}

# splice new actions before DO_NOTHING
actions = dict(cfg["named_actions"])
do_nothing = {"DO_NOTHING": actions.pop("DO_NOTHING")}
actions.update(new_actions)
actions.update(do_nothing)
cfg["named_actions"] = actions

# ── 2. NEW DESCRIPTIONS ───────────────────────────────────────────────────────
new_descs = {
    "ROAD_NUDGE_LEFT":    "A 300ms then W 700ms -- micro-steer left while re-accelerating. Use when the car has just barely drifted off the right edge of the road and the road is immediately to the left.",
    "ROAD_NUDGE_RIGHT":   "D 300ms then W 700ms -- micro-steer right while re-accelerating. Use when the car has just barely drifted off the left edge of the road and the road is immediately to the right.",
    "ROAD_RETURN_LEFT":   "S 500ms → W+A 700ms → W 900ms -- brake, steer left back onto road, re-accelerate. Use when car has gone noticeably off road on the right side and needs to return to tarmac.",
    "ROAD_RETURN_RIGHT":  "S 500ms → W+D 700ms → W 900ms -- brake, steer right back onto road, re-accelerate. Use when car has gone noticeably off road on the left side and needs to return to tarmac.",
    "ROAD_RECOVER_LEFT":  "Hard brake → steer left → drive back onto road → accelerate. Use when car is deep in grass/dirt on the right side or has hit a barrier and needs a full road-return sequence.",
    "ROAD_RECOVER_RIGHT": "Hard brake → steer right → drive back onto road → accelerate. Use when car is deep in grass/dirt on the left side or has hit a barrier on the left and needs a full road-return sequence.",
}
cfg["named_action_descriptions"].update(new_descs)

# ── 3. INSERT NEW RULE after existing RULE 3 (stuck) ─────────────────────────
NEW_RULE = [
    "RULE 3b -- OFF ROAD / DRIFTED OFF TRACK [highest road-priority rule]:",
    "  The car is NOT on asphalt -- grass, dirt, gravel, or sand is clearly visible",
    "  UNDER or AROUND the car, AND this is NOT a cross-country / dirt race event.",
    "  The goal is always: SLOW DOWN → REALIGN → RETURN TO ROAD → SPEED UP.",
    "",
    "  STEP 1 -- HOW FAR OFF ROAD?",
    "    Barely off (road edge visible immediately beside the car, just one or two wheels on grass):",
    "    Road is to the LEFT (car drifted right):",
    "    => ROAD_NUDGE_LEFT   (gentle steer left to ease back onto tarmac while keeping momentum)",
    "    Road is to the RIGHT (car drifted left):",
    "    => ROAD_NUDGE_RIGHT  (gentle steer right to ease back onto tarmac while keeping momentum)",
    "",
    "  STEP 2 -- Significantly off road (more than half car width off tarmac):",
    "    Road is clearly to the LEFT of the car:",
    "    => ROAD_RETURN_LEFT  (brake → steer left back to road → re-accelerate)",
    "    Road is clearly to the RIGHT of the car:",
    "    => ROAD_RETURN_RIGHT (brake → steer right back to road → re-accelerate)",
    "",
    "  STEP 3 -- Deeply off road / hit roadside barrier (car is far from tarmac or has bounced):",
    "    Road surface is to the LEFT after the barrier:",
    "    => ROAD_RECOVER_LEFT  (hard brake → turn left → build speed back on road)",
    "    Road surface is to the RIGHT after the barrier:",
    "    => ROAD_RECOVER_RIGHT (hard brake → turn right → build speed back on road)",
    "",
    "  AFTER RETURNING TO ROAD:",
    "    Once tarmac is under all four wheels again, immediately switch to a normal",
    "    driving action: THROTTLE_LIGHT -> THROTTLE_MEDIUM -> FULL_THROTTLE",
    "    Do NOT keep using road-return actions once back on asphalt.",
    "",
    "  HOW TO DETECT 'off road':",
    "    - Green grass / brown dirt / gravel texture visible under the car",
    "    - Road edge (white line or tarmac edge) is to one side, not under the car",
    "    - The racing line / magenta arrow leads back to the left or right, not straight ahead",
    "    - No tarmac visible directly ahead for more than a car length",
    "",
]

# Find the index of the line that starts RULE 4 and insert before it
rules = cfg["decision_rules"]
insert_at = None
for i, line in enumerate(rules):
    if line.startswith("RULE 4 --"):
        insert_at = i
        break

if insert_at is not None:
    cfg["decision_rules"] = rules[:insert_at] + NEW_RULE + rules[insert_at:]
    print(f"Inserted RULE 3b at line index {insert_at}")
else:
    cfg["decision_rules"] += NEW_RULE
    print("RULE 4 not found -- appended new rule at end")

# ── 4. STRENGTHEN CONSTRAINTS ─────────────────────────────────────────────────
road_constraints = [
    "* ROAD PRIORITY: staying on tarmac is ALWAYS the #1 goal in road/street racing events. Never sacrifice road position for speed.",
    "* When off road: ALWAYS slow down first (tap S), THEN steer back to tarmac, THEN re-accelerate. Never floor it while on grass.",
    "* After any road-return action, check the next screenshot -- if back on asphalt, switch to THROTTLE_LIGHT then build up.",
    "* The racing line (magenta/pink strip on road) shows where to drive. If it is off to one side, you have drifted off course -- correct immediately.",
]
# Insert road constraints at the start so they are highest-visibility
cfg["constraints"] = road_constraints + cfg["constraints"]

# ── 5. UPDATE CHECKLIST ───────────────────────────────────────────────────────
# Insert "are we off road?" as question 3b right after question 3 (stuck)
checklist = cfg["situation_checklist"]
new_q = "  3b. Is the car on GRASS / DIRT / SAND in a road/street race (NOT cross-country)? -> RULE 3b (ROAD_RETURN_*/ROAD_NUDGE_*)"
insert_q_at = None
for i, line in enumerate(checklist):
    if "RULE 3" in line and "stuck" in line.lower():
        insert_q_at = i + 1
        break
if insert_q_at is not None:
    checklist.insert(insert_q_at, new_q)
cfg["situation_checklist"] = checklist

# ── 6. WRITE ──────────────────────────────────────────────────────────────────
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"config.json updated  ({p.stat().st_size:,} bytes)")
print(f"  named_actions       : {len(cfg['named_actions'])}")
print(f"  decision_rules      : {len(cfg['decision_rules'])} lines")
print(f"  constraints         : {len(cfg['constraints'])} items")
print(f"  situation_checklist : {len(cfg['situation_checklist'])} items")
