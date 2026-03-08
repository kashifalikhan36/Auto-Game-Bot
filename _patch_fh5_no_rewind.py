"""
Patches FH5 config.json to completely remove Rewind:
  - Deletes REWIND and REWIND_HOLD from named_actions + descriptions
  - Rewrites every rule that referenced REWIND -> manual unstick/recovery
  - Adds hard NEVER constraint
  - Removes REWIND from checklist
"""
import json, pathlib

p = pathlib.Path("games_config/forza_horizon_5/config.json")
cfg = json.loads(p.read_text(encoding="utf-8"))

# ── 1. Remove from named_actions ───────────────────────────────────────────
for key in ("REWIND", "REWIND_HOLD"):
    cfg["named_actions"].pop(key, None)
    cfg["named_action_descriptions"].pop(key, None)
print("Removed REWIND/REWIND_HOLD from named_actions")

# ── 2. Rewrite decision_rules ──────────────────────────────────────────────
# Replace the block of RULE 2 and RULE 3 wholesale because they both say => REWIND.
# Strategy: iterate and rebuild the list, swapping out any line containing "REWIND".

REWIND_RULE2 = [
    "RULE 2 -- CRASH / SPIN / WRONG DIRECTION [second override]:",
    "  Car has collided hard (airbag animation, crash sound cue visible in replay),",
    "  car is facing more than ~90 degrees from the intended direction,",
    "  car has stopped or is stationary in the middle of a race,",
    "  or the car has fallen off the road / off a cliff",
    "  => REWIND  (always prefer Rewind over trying to drive out of a bad position)",
    "  If Rewind was picked but car appears stuck against same obstacle next frame:",
    "  => REWIND_HOLD  (hold R longer to go further back)",
]
REWIND_RULE2_NEW = [
    "RULE 2 -- CRASH / SPIN / WRONG DIRECTION [second override]:",
    "  Car has collided hard, car is facing more than ~90 degrees from intended direction,",
    "  car has stopped in race, or car has gone off a cliff / deep off road.",
    "  DO NOT use Rewind. Recover manually:",
    "  Car is facing left of road (spun counterclockwise):",
    "  => SPIN_RECOVER_LEFT   (W+D to countersteer back onto road heading)",
    "  Car is facing right of road (spun clockwise):",
    "  => SPIN_RECOVER_RIGHT  (W+A to countersteer back onto road heading)",
    "  Car has hit a barrier and stopped -- space behind on LEFT:",
    "  => UNSTICK_REVERSE_LEFT   (S+A to reverse away, then steer back to road)",
    "  Car has hit a barrier and stopped -- space behind on RIGHT:",
    "  => UNSTICK_REVERSE_RIGHT  (S+D to reverse away, then steer back to road)",
    "  Car has stopped facing correct direction but off road:",
    "  => ROAD_RETURN_LEFT  or  ROAD_RETURN_RIGHT  (depending on which side road is)",
]

REWIND_RULE3 = [
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
]
REWIND_RULE3_NEW = [
    "RULE 3 -- STUCK IN TERRAIN / AGAINST WALL:",
    "  Car is moving very slowly or not at all, wheels in air, or same wall fills view repeatedly.",
    "  DO NOT use Rewind. Recover manually:",
    "  Clear space behind on the LEFT:",
    "  => UNSTICK_REVERSE_LEFT   (S+A reverse + steer away from wall)",
    "  Clear space behind on the RIGHT:",
    "  => UNSTICK_REVERSE_RIGHT  (S+D reverse + steer away from wall)",
    "  No clear space either side -- reverse straight then assess:",
    "  => UNSTICK_REVERSE        (S reverse, then pick a steering direction)",
]

def replace_block(rules, old_block, new_block):
    old_str = "\n".join(old_block)
    rules_str = "\n".join(rules)
    if old_str in rules_str:
        rules_str = rules_str.replace(old_str, "\n".join(new_block), 1)
        print(f"  Replaced block starting with: {old_block[0][:60]}")
        return rules_str.split("\n")
    else:
        print(f"  WARNING: could not find block: {old_block[0][:60]}")
        return rules

rules = cfg["decision_rules"]
rules = replace_block(rules, REWIND_RULE2, REWIND_RULE2_NEW)
rules = replace_block(rules, REWIND_RULE3, REWIND_RULE3_NEW)

# Safety net: replace any remaining stray "=> REWIND" / "=> REWIND_HOLD" lines
cleaned = []
for line in rules:
    if "=> REWIND_HOLD" in line:
        cleaned.append(line.replace("=> REWIND_HOLD", "=> UNSTICK_REVERSE  (manual reverse -- no Rewind)"))
    elif "=> REWIND" in line and "DO NOT" not in line:
        cleaned.append(line.replace("=> REWIND", "=> UNSTICK_REVERSE  (manual reverse -- no Rewind)"))
    else:
        cleaned.append(line)
cfg["decision_rules"] = cleaned

remaining = [l for l in cfg["decision_rules"] if "REWIND" in l and "DO NOT" not in l and "never" not in l.lower()]
if remaining:
    print("  Remaining REWIND references (manual check):")
    for l in remaining:
        print("   ", l)
else:
    print("  No stray REWIND references left in rules")

# ── 3. Add hard constraint (prepend) ──────────────────────────────────────
NEVER_REWIND = "* NEVER use REWIND or REWIND_HOLD. Rewind is disabled. Always recover manually: reverse out, spin-correct, or use road-return actions."
cfg["constraints"].insert(0, NEVER_REWIND)
print("Added NEVER constraint at front")

# ── 4. Update checklist -- remove REWIND mention from question 2 ───────────
cfg["situation_checklist"] = [
    line.replace("-> RULE 2  (REWIND)", "-> RULE 2  (SPIN_RECOVER_*/UNSTICK_REVERSE_*)")
        .replace("-> RULE 3  (REWIND/UNSTICK)", "-> RULE 3  (UNSTICK_REVERSE_*)")
    for line in cfg["situation_checklist"]
]
print("Updated checklist")

# ── 5. Write ───────────────────────────────────────────────────────────────
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nconfig.json updated  ({p.stat().st_size:,} bytes)")
print(f"  named_actions  : {len(cfg['named_actions'])}")
print(f"  decision_rules : {len(cfg['decision_rules'])} lines")
print(f"  constraints    : {len(cfg['constraints'])} items")
print(f"  REWIND in named_actions: {'REWIND' in cfg['named_actions'] or 'REWIND_HOLD' in cfg['named_actions']}")
