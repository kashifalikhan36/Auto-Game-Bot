"""
Patches FH5 config.json to stop straight-road oscillation:
  1. Reduce ACCEL_LEFT/RIGHT_GENTLE hold_ms: 800 -> 220ms  (stop overshooting)
  2. Reduce ACCEL_LEFT/RIGHT_MEDIUM hold_ms: keep corner speed but trim
  3. Add NUDGE_LEFT / NUDGE_RIGHT micro-correction actions (150ms tap, no throttle needed)
  4. Tighten RULE 10 (corner): gentle curve ONLY if road actually curves, not just racing line
  5. Add straight-road constraint: racing line offset is NOT a reason to steer
  6. Add nudge actions to named_action_descriptions
"""
import json, pathlib

p = pathlib.Path("games_config/forza_horizon_5/config.json")
cfg = json.loads(p.read_text(encoding="utf-8"))

acts = cfg["named_actions"]
desc = cfg["named_action_descriptions"]

# ══════════════════════════════════════════════════════
# 1. Shrink hold_ms on gentle steering -- stops oscillation on straights
# ══════════════════════════════════════════════════════
for action, new_hold in [
    ("ACCEL_LEFT_GENTLE",  220),
    ("ACCEL_RIGHT_GENTLE", 220),
    ("ACCEL_LEFT_MEDIUM",  450),
    ("ACCEL_RIGHT_MEDIUM", 450),
]:
    if action in acts:
        for track in acts[action]:
            if "hold_ms" in track:
                old = track["hold_ms"]
                track["hold_ms"] = new_hold
                print(f"  {action}: hold_ms {old} -> {new_hold}")

# ══════════════════════════════════════════════════════
# 2. Add NUDGE_LEFT and NUDGE_RIGHT (tiny tap for micro-correction on straights)
# ══════════════════════════════════════════════════════
# Insert just before DO_NOTHING
action_names = list(acts.keys())
insert_before = "DO_NOTHING"
insert_idx = action_names.index(insert_before) if insert_before in action_names else len(action_names)

new_actions = {
    "NUDGE_LEFT": [{"keys": ["a"], "hold_ms": 140}],
    "NUDGE_RIGHT": [{"keys": ["d"], "hold_ms": 140}],
}
new_descs = {
    "NUDGE_LEFT":  "Micro-correction on a straight: tap A for 140ms to gently re-centre the car on the road without losing speed. Use ONLY when the car is drifting slightly right of the road centre on a straight — never on a corner.",
    "NUDGE_RIGHT": "Micro-correction on a straight: tap D for 140ms to gently re-centre the car on the road without losing speed. Use ONLY when the car is drifting slightly left of the road centre on a straight — never on a corner.",
}

# Rebuild ordered dict with nudges just before DO_NOTHING
rebuilt_acts = {}
for k in action_names:
    if k == insert_before:
        for nk, nv in new_actions.items():
            rebuilt_acts[nk] = nv
    rebuilt_acts[k] = acts[k]
cfg["named_actions"] = rebuilt_acts

rebuilt_desc = {}
for k in list(desc.keys()):
    if k == insert_before:
        for nk, nv in new_descs.items():
            rebuilt_desc[nk] = nv
    rebuilt_desc[k] = desc[k]
cfg["named_action_descriptions"] = rebuilt_desc
print(f"Added NUDGE_LEFT and NUDGE_RIGHT actions")

# ══════════════════════════════════════════════════════
# 3. Tighten constraints for straight-road behaviour
# ══════════════════════════════════════════════════════
STRAIGHT_CONSTRAINTS = [
    "* On a STRAIGHT road: pick FULL_THROTTLE by default. Use NUDGE_LEFT or NUDGE_RIGHT (NOT ACCEL_*_GENTLE) for micro-corrections if the car is drifting sideways. ACCEL_*_GENTLE is ONLY for when the road itself visibly curves.",
    "* The racing line (magenta strip) being slightly to one side on a straight does NOT mean you should steer — it is the ideal apex line, not a target to chase. Only steer when the ROAD EDGE itself curves.",
    "* NEVER alternate LEFT steer then RIGHT steer on consecutive frames on a straight road — this causes oscillation. If you just picked a left action, pick FULL_THROTTLE next unless the road curves further left.",
]
# Insert after the 3 forward-bias constraints (indices 1,2,3) -> at index 4
for i, c in enumerate(STRAIGHT_CONSTRAINTS):
    cfg["constraints"].insert(4 + i, c)
print(f"Constraints now: {len(cfg['constraints'])} items")

# ══════════════════════════════════════════════════════
# 4. Update RULE 10 gentle curve condition to be explicit
# ══════════════════════════════════════════════════════
rules_str = "\n".join(cfg["decision_rules"])

OLD_GENTLE = (
    "  GENTLE LEFT curve ahead:\n"
    "  => ACCEL_LEFT_GENTLE\n"
    "  MEDIUM LEFT corner ahead, enough speed to use braking line:\n"
    "  => ACCEL_LEFT_MEDIUM"
)
NEW_GENTLE = (
    "  GENTLE LEFT curve ahead (the ROAD EDGE itself bends left -- NOT just the racing line shifting):\n"
    "  => ACCEL_LEFT_GENTLE  (only 220ms steer -- do not hold; re-assess next frame)\n"
    "  MEDIUM LEFT corner ahead, enough speed to use braking line:\n"
    "  => ACCEL_LEFT_MEDIUM"
)
if OLD_GENTLE in rules_str:
    rules_str = rules_str.replace(OLD_GENTLE, NEW_GENTLE, 1)
    print("Patched RULE 10 gentle LEFT curve condition")
else:
    print("WARNING: could not find RULE 10 gentle LEFT to patch")

OLD_GENTLE_R = (
    "  GENTLE RIGHT curve ahead:\n"
    "  => ACCEL_RIGHT_GENTLE"
)
NEW_GENTLE_R = (
    "  GENTLE RIGHT curve ahead (the ROAD EDGE itself bends right -- NOT just the racing line shifting):\n"
    "  => ACCEL_RIGHT_GENTLE  (only 220ms steer -- do not hold; re-assess next frame)"
)
if OLD_GENTLE_R in rules_str:
    rules_str = rules_str.replace(OLD_GENTLE_R, NEW_GENTLE_R, 1)
    print("Patched RULE 10 gentle RIGHT curve condition")
else:
    print("WARNING: could not find RULE 10 gentle RIGHT to patch")

# ══════════════════════════════════════════════════════
# 5. Update RULE 15 to mention NUDGE for micro-correcting
# ══════════════════════════════════════════════════════
OLD_R15 = (
    "  Long straight road, no obstacles, no corners visible yet:\n"
    "  => FULL_THROTTLE  *** THIS IS THE MOST COMMON CORRECT ANSWER ***"
)
NEW_R15 = (
    "  Long straight road, no obstacles, no corners visible yet:\n"
    "  => FULL_THROTTLE  *** THIS IS THE MOST COMMON CORRECT ANSWER ***\n"
    "  Car drifting slightly to the RIGHT of road centre (not near edge, not a corner):\n"
    "  => NUDGE_LEFT  (140ms tap A -- micro-correct without losing speed)\n"
    "  Car drifting slightly to the LEFT of road centre (not near edge, not a corner):\n"
    "  => NUDGE_RIGHT  (140ms tap D -- micro-correct without losing speed)"
)
if OLD_R15 in rules_str:
    rules_str = rules_str.replace(OLD_R15, NEW_R15, 1)
    print("Patched RULE 15 with NUDGE micro-correction options")
else:
    print("WARNING: could not find RULE 15 FULL_THROTTLE line to patch")

cfg["decision_rules"] = rules_str.split("\n")

# ══════════════════════════════════════════════════════
# 6. Update checklist to mention NUDGE on straight
# ══════════════════════════════════════════════════════
cfg["situation_checklist"] = [
    line.replace(
        "14. Is the road ahead clear OR have none of questions 1-13 been answered YES? -> RULE 15 (FULL_THROTTLE)",
        "14. Is the road ahead clear straight asphalt? -> RULE 15 (FULL_THROTTLE; or NUDGE_LEFT/RIGHT for tiny drift correction)"
    )
    for line in cfg["situation_checklist"]
]

# ══════════════════════════════════════════════════════
# 7. Write + verify
# ══════════════════════════════════════════════════════
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nconfig.json updated  ({p.stat().st_size:,} bytes)")
print(f"  named_actions  : {len(cfg['named_actions'])}")
print(f"  constraints    : {len(cfg['constraints'])} items")
print(f"  decision_rules : {len(cfg['decision_rules'])} lines")

acts2 = cfg["named_actions"]
print(f"  NUDGE_LEFT hold_ms   : {acts2['NUDGE_LEFT'][0]['hold_ms']}")
print(f"  NUDGE_RIGHT hold_ms  : {acts2['NUDGE_RIGHT'][0]['hold_ms']}")
print(f"  ACCEL_LEFT_GENTLE    : {acts2['ACCEL_LEFT_GENTLE'][0]['hold_ms']}ms")
print(f"  ACCEL_RIGHT_GENTLE   : {acts2['ACCEL_RIGHT_GENTLE'][0]['hold_ms']}ms")
r_text = "\n".join(cfg["decision_rules"])
print(f"  RULE 10 gentle road-edge note: {'ROAD EDGE itself bends' in r_text}")
print(f"  RULE 15 NUDGE options: {'NUDGE_LEFT' in r_text}")
c_text = "\n".join(cfg["constraints"])
print(f"  No-oscillation constraint: {'alternate LEFT steer then RIGHT' in c_text}")
