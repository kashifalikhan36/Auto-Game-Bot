"""
Patches FH5 config.json:
  1. Unstick actions -> proper rock sequence: S(back) -> W+steer(forward+turn to escape)
  2. Road-return/nudge final throttle trimmed -> THROTTLE_LIGHT pace, not aggressive
  3. RULE 3 -> explain rock-repeat technique
  4. RULE 4 -> after returning to road, stay slow until road is straight/clear
  5. Add post-recovery speed constraint
"""
import json, pathlib

p = pathlib.Path("games_config/forza_horizon_5/config.json")
cfg = json.loads(p.read_text(encoding="utf-8"))

acts = cfg["named_actions"]
desc = cfg["named_action_descriptions"]

# ══════════════════════════════════════════════════════════════════════════════
# 1. FIX UNSTICK SEQUENCES
#    Old: single key press (S+A 700ms = reverse while steering)
#    New: S back a little -> then W+steer to drive forward out of the stuck spot
# ══════════════════════════════════════════════════════════════════════════════

# UNSTICK_REVERSE_LEFT  -- back a little, then throttle + left to pull away right
acts["UNSTICK_REVERSE_LEFT"] = [{
    "sequence": [
        {"keys": ["s"],      "hold_ms": 350, "delay_after_ms": 80},   # brief reverse
        {"keys": ["w", "a"], "hold_ms": 650, "delay_after_ms": 60},   # throttle + left
        {"keys": ["s"],      "hold_ms": 250, "delay_after_ms": 60},   # back a touch more if needed
        {"keys": ["w", "a"], "hold_ms": 500},                         # throttle + left again
    ]
}]
desc["UNSTICK_REVERSE_LEFT"] = (
    "Unstick sequence: reverse briefly (S 350ms) then drive forward-left (W+A 650ms) "
    "to rock free from wall/tree on the left. Repeats back→forward twice. "
    "Use when stuck against a tree or wall with escape space to the LEFT."
)

# UNSTICK_REVERSE_RIGHT -- back a little, then throttle + right to pull away left
acts["UNSTICK_REVERSE_RIGHT"] = [{
    "sequence": [
        {"keys": ["s"],      "hold_ms": 350, "delay_after_ms": 80},   # brief reverse
        {"keys": ["w", "d"], "hold_ms": 650, "delay_after_ms": 60},   # throttle + right
        {"keys": ["s"],      "hold_ms": 250, "delay_after_ms": 60},   # back a touch more
        {"keys": ["w", "d"], "hold_ms": 500},                         # throttle + right again
    ]
}]
desc["UNSTICK_REVERSE_RIGHT"] = (
    "Unstick sequence: reverse briefly (S 350ms) then drive forward-right (W+D 650ms) "
    "to rock free from wall/tree on the right. Repeats back→forward twice. "
    "Use when stuck against a tree or wall with escape space to the RIGHT."
)

# UNSTICK_REVERSE -- stuck, no clear direction: reverse straight then try forward
acts["UNSTICK_REVERSE"] = [{
    "sequence": [
        {"keys": ["s"],  "hold_ms": 450, "delay_after_ms": 80},   # reverse straight
        {"keys": ["w"],  "hold_ms": 500, "delay_after_ms": 60},   # try forward
        {"keys": ["s"],  "hold_ms": 300, "delay_after_ms": 60},   # back a bit more
        {"keys": ["w"],  "hold_ms": 400},                         # try forward again
    ]
}]
desc["UNSTICK_REVERSE"] = (
    "Unstick sequence: reverse straight (S 450ms) then attempt forward (W 500ms), "
    "repeated twice to rock free. Use when blocked and no clear left/right escape. "
    "After this, assess direction and pick UNSTICK_REVERSE_LEFT or RIGHT."
)

print("Fixed UNSTICK_REVERSE, UNSTICK_REVERSE_LEFT, UNSTICK_REVERSE_RIGHT sequences")

# ══════════════════════════════════════════════════════════════════════════════
# 2. TRIM ROAD-RETURN FINAL THROTTLE -> slow, not aggressive
#    Goal: get back on tarmac gently, then build speed over next frames
# ══════════════════════════════════════════════════════════════════════════════

# ROAD_NUDGE_LEFT / RIGHT -- barely off road, light steer then gentle throttle pulse
acts["ROAD_NUDGE_LEFT"] = [{"sequence": [
    {"keys": ["a"], "hold_ms": 300, "delay_after_ms": 50},
    {"keys": ["w"], "hold_ms": 350},   # was 700ms -- now a short pulse
]}]
acts["ROAD_NUDGE_RIGHT"] = [{"sequence": [
    {"keys": ["d"], "hold_ms": 300, "delay_after_ms": 50},
    {"keys": ["w"], "hold_ms": 350},
]}]
desc["ROAD_NUDGE_LEFT"] = (
    "Barely off right edge: steer left (A 300ms) then light throttle pulse (W 350ms). "
    "Returns 1-2 tyres back to tarmac. Keep speed low after -- use THROTTLE_LIGHT on next frame."
)
desc["ROAD_NUDGE_RIGHT"] = (
    "Barely off left edge: steer right (D 300ms) then light throttle pulse (W 350ms). "
    "Returns 1-2 tyres back to tarmac. Keep speed low after -- use THROTTLE_LIGHT on next frame."
)

# ROAD_RETURN_LEFT / RIGHT -- significantly off, brake+steer back, slow final throttle
acts["ROAD_RETURN_LEFT"] = [{"sequence": [
    {"keys": ["s"],      "hold_ms": 500, "delay_after_ms": 100},
    {"keys": ["w", "a"], "hold_ms": 600, "delay_after_ms": 80},
    {"keys": ["w"],      "hold_ms": 350},   # was 900ms -- now just a gentle pulse
]}]
acts["ROAD_RETURN_RIGHT"] = [{"sequence": [
    {"keys": ["s"],      "hold_ms": 500, "delay_after_ms": 100},
    {"keys": ["w", "d"], "hold_ms": 600, "delay_after_ms": 80},
    {"keys": ["w"],      "hold_ms": 350},
]}]
desc["ROAD_RETURN_LEFT"] = (
    "S 500ms (brake) → W+A 600ms (steer left back to road) → W 350ms (gentle throttle). "
    "Returns car to tarmac. After this action, use THROTTLE_LIGHT and assess road direction before speeding up."
)
desc["ROAD_RETURN_RIGHT"] = (
    "S 500ms (brake) → W+D 600ms (steer right back to road) → W 350ms (gentle throttle). "
    "Returns car to tarmac. After this action, use THROTTLE_LIGHT and assess road direction before speeding up."
)

# ROAD_RECOVER_LEFT / RIGHT -- deep off road, hard brake+steer, slow finale
acts["ROAD_RECOVER_LEFT"] = [{"sequence": [
    {"keys": ["s"],      "hold_ms": 700, "delay_after_ms": 120},
    {"keys": ["a"],      "hold_ms": 450, "delay_after_ms": 80},
    {"keys": ["w", "a"], "hold_ms": 550, "delay_after_ms": 60},
    {"keys": ["w"],      "hold_ms": 350},   # was 1200ms -- now a gentle pulse only
]}]
acts["ROAD_RECOVER_RIGHT"] = [{"sequence": [
    {"keys": ["s"],      "hold_ms": 700, "delay_after_ms": 120},
    {"keys": ["d"],      "hold_ms": 450, "delay_after_ms": 80},
    {"keys": ["w", "d"], "hold_ms": 550, "delay_after_ms": 60},
    {"keys": ["w"],      "hold_ms": 350},
]}]
desc["ROAD_RECOVER_LEFT"] = (
    "Deep off-road recovery left: hard brake (S 700ms) → steer left alone (A 450ms) → "
    "drive back onto road (W+A 550ms) → gentle pulse (W 350ms). "
    "After this, stay at THROTTLE_LIGHT until road is straight and clear."
)
desc["ROAD_RECOVER_RIGHT"] = (
    "Deep off-road recovery right: hard brake (S 700ms) → steer right alone (D 450ms) → "
    "drive back onto road (W+D 550ms) → gentle pulse (W 350ms). "
    "After this, stay at THROTTLE_LIGHT until road is straight and clear."
)

print("Fixed ROAD_NUDGE / ROAD_RETURN / ROAD_RECOVER final throttle values")

# ══════════════════════════════════════════════════════════════════════════════
# 3. UPDATE RULE 3 -- explain the rock-repeat technique clearly
# ══════════════════════════════════════════════════════════════════════════════
rules_str = "\n".join(cfg["decision_rules"])

OLD_R3 = (
    "RULE 3 -- COMPLETELY STOPPED AGAINST A WALL / BARRIER  [reverse only here]:\n"
    "  ONLY applies when: speedometer reads zero, W pressed gives no forward movement,\n"
    "  and a wall / barrier / rock is visibly blocking the front of the car.\n"
    "  This rule is rare -- under 2% of frames. Do not trigger it unless truly stopped.\n"
    "\n"
    "  Open space behind on the LEFT (steer A while reversing):\n"
    "  => UNSTICK_REVERSE_LEFT\n"
    "  Open space behind on the RIGHT (steer D while reversing):\n"
    "  => UNSTICK_REVERSE_RIGHT\n"
    "  No clear direction visible -- reverse straight first then re-assess:\n"
    "  => UNSTICK_REVERSE"
)
NEW_R3 = (
    "RULE 3 -- COMPLETELY STOPPED AGAINST A WALL / TREE / BARRIER  [reverse only here]:\n"
    "  ONLY applies when: car is NOT moving (speed = 0), W gives no forward motion,\n"
    "  and a wall, tree, or barrier is visibly blocking the front of the car.\n"
    "  This rule is rare -- under 2% of frames. Do not trigger unless truly stopped.\n"
    "\n"
    "  TECHNIQUE -- rock the car to break free:\n"
    "    1. Reverse a LITTLE (S ~350ms) to create space\n"
    "    2. Then immediately throttle + steer away from the obstacle (W+A or W+D)\n"
    "    3. Repeat this back-forward-back-forward rocking until the car breaks free\n"
    "    4. Once moving freely, switch to THROTTLE_LIGHT and steer back toward road\n"
    "\n"
    "  Space to escape LEFT -- pick LEFT rock action (S back → W+A forward-left):\n"
    "  => UNSTICK_REVERSE_LEFT\n"
    "  Space to escape RIGHT -- pick RIGHT rock action (S back → W+D forward-right):\n"
    "  => UNSTICK_REVERSE_RIGHT\n"
    "  No clear direction -- reverse straight then try forward:\n"
    "  => UNSTICK_REVERSE\n"
    "\n"
    "  AFTER BREAKING FREE:\n"
    "    Car starts moving? Immediately switch to THROTTLE_LIGHT.\n"
    "    Steer gently back toward the road. Do NOT go FULL_THROTTLE until on tarmac."
)

if OLD_R3 in rules_str:
    rules_str = rules_str.replace(OLD_R3, NEW_R3, 1)
    print("Patched RULE 3 with rock-repeat technique")
else:
    print("WARNING: RULE 3 text not found exactly -- checking partial...")
    if "COMPLETELY STOPPED AGAINST A WALL" in rules_str:
        print("  Rule 3 header found but content differs -- manual check needed")
    else:
        print("  Rule 3 not found at all")

# ══════════════════════════════════════════════════════════════════════════════
# 4. UPDATE RULE 4 -- after returning to road, stay slow until straight/clear
# ══════════════════════════════════════════════════════════════════════════════
OLD_R4_AFTER = (
    "  AFTER RETURNING TO TARMAC:\n"
    "    All four wheels back on asphalt? Immediately switch BACK to normal driving:\n"
    "    THROTTLE_LIGHT (1 frame) → THROTTLE_MEDIUM (1-2 frames) → FULL_THROTTLE\n"
    "    Do NOT keep using road-return actions once tyres are on asphalt."
)
NEW_R4_AFTER = (
    "  AFTER RETURNING TO TARMAC:\n"
    "    All four wheels back on asphalt? Follow this MANDATORY speed build sequence:\n"
    "\n"
    "    STEP A -- Tyres just touched tarmac: use THROTTLE_LIGHT for 2-3 frames\n"
    "              Keep steering straight. Let the car settle and align with road.\n"
    "    STEP B -- Car is straight on road, road ahead is clear for a few seconds:\n"
    "              Move up to THROTTLE_MEDIUM for 1-2 frames.\n"
    "    STEP C -- Road is clearly straight and open with no obstacles or corners:\n"
    "              Now use FULL_THROTTLE.\n"
    "\n"
    "    NEVER jump from a recovery action straight to FULL_THROTTLE.\n"
    "    NEVER speed up while the road is still curving or has obstacles ahead.\n"
    "    Do NOT keep using road-return actions once all tyres are on asphalt."
)

if OLD_R4_AFTER in rules_str:
    rules_str = rules_str.replace(OLD_R4_AFTER, NEW_R4_AFTER, 1)
    print("Patched RULE 4 after-return speed build")
else:
    print("WARNING: RULE 4 after-return block not found exactly")

cfg["decision_rules"] = rules_str.split("\n")

# ══════════════════════════════════════════════════════════════════════════════
# 5. ADD POST-RECOVERY CONSTRAINT + SLOW-ON-ROAD CONSTRAINT
# ══════════════════════════════════════════════════════════════════════════════
# Find the index of the off-road constraint to insert next to it
constraint_idx = next(
    (i for i,c in enumerate(cfg["constraints"]) if "off road" in c.lower() and "slow down" in c.lower()),
    len(cfg["constraints"]) - 3   # fallback: near end
)

new_constraints = [
    "* After ANY recovery action (UNSTICK_*, ROAD_RETURN_*, ROAD_RECOVER_*, ROAD_NUDGE_*): use THROTTLE_LIGHT for the next 2-3 frames. Do NOT jump to FULL_THROTTLE immediately after a recovery.",
    "* On road after recovery: stay at THROTTLE_LIGHT until the road ahead is visibly straight and clear of obstacles/corners. Only then step up to THROTTLE_MEDIUM, then FULL_THROTTLE.",
    "* After being stuck (RULE 3): once moving, keep speed LOW and steer gently back toward the road. Resist the urge to accelerate -- get back on tarmac FIRST, then speed up.",
]
for i, c in enumerate(new_constraints):
    cfg["constraints"].insert(constraint_idx + 1 + i, c)

print(f"Added {len(new_constraints)} post-recovery constraints")
print(f"Constraints now: {len(cfg['constraints'])} items")

# ══════════════════════════════════════════════════════════════════════════════
# 6. WRITE + VERIFY
# ══════════════════════════════════════════════════════════════════════════════
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nconfig.json updated  ({p.stat().st_size:,} bytes)")
print(f"  named_actions  : {len(cfg['named_actions'])}")
print(f"  decision_rules : {len(cfg['decision_rules'])} lines")
print(f"  constraints    : {len(cfg['constraints'])} items")

# Verify sequences
a = cfg["named_actions"]
for name in ["UNSTICK_REVERSE_LEFT","UNSTICK_REVERSE_RIGHT","UNSTICK_REVERSE"]:
    seq = a[name][0].get("sequence", [])
    steps = [f"{s['keys']}x{s['hold_ms']}ms" for s in seq]
    print(f"  {name}: {' -> '.join(steps)}")

for name in ["ROAD_RETURN_LEFT","ROAD_RECOVER_LEFT"]:
    seq = a[name][0].get("sequence", [])
    last_hold = seq[-1]["hold_ms"]
    print(f"  {name} final throttle: {last_hold}ms")

r_text = "\n".join(cfg["decision_rules"])
print(f"  RULE 3 rock-repeat present : {'rock the car to break free' in r_text}")
print(f"  RULE 4 STEP A/B/C present  : {'STEP A' in r_text and 'STEP C' in r_text}")
c_text = "\n".join(cfg["constraints"])
print(f"  Post-recovery THROTTLE_LIGHT constraint: {'THROTTLE_LIGHT for the next' in c_text}")
