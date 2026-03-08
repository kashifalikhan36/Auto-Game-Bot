"""
Patches FH5 config.json:
  1. RULE 13 (OFFROAD) -- add super-explicit trigger conditions so LLM never picks
     OFFROAD_THROTTLE during a road race just because grass is beside the road.
  2. Add hard constraint: OFFROAD_* only during cross-country events, never road races.
  3. Fix RULE 4 (off road in road race) vs RULE 13 distinction to be crystal clear.
"""
import json, pathlib

p = pathlib.Path("games_config/forza_horizon_5/config.json")
cfg = json.loads(p.read_text(encoding="utf-8"))

rules_str = "\n".join(cfg["decision_rules"])

# ══════════════════════════════════════════════════════════════════════════════
# 1. Rewrite RULE 13 with much clearer trigger conditions
# ══════════════════════════════════════════════════════════════════════════════
OLD_R13 = (
    "RULE 13 -- CROSS COUNTRY / DIRT RACE EVENT  (off-road terrain expected):\n"
    "  No asphalt visible, rough terrain, cross-country checkpoints shown on map.\n"
    "  Path clear ahead -- drive on:\n"
    "  => OFFROAD_THROTTLE\n"
    "  Rock / tree / fence on the RIGHT, go around to the left:\n"
    "  => OFFROAD_LEFT\n"
    "  Rock / tree / fence on the LEFT, go around to the right:\n"
    "  => OFFROAD_RIGHT\n"
    "  Very rough section (rocks, steep slope, river, deep ruts) -- pick way carefully:\n"
    "  => OFFROAD_CAREFUL"
)
NEW_R13 = (
    "RULE 13 -- CROSS COUNTRY / DIRT RACE EVENT ONLY:\n"
    "  *** CRITICAL: Only use this rule when ALL of these are true: ***\n"
    "    - The game HUD / event name explicitly says 'Cross Country', 'Dirt Racing',\n"
    "      'Trailblazer', or similar off-road event type\n"
    "    - There is NO paved tarmac road visible anywhere ahead of the car\n"
    "    - The checkpoints/racing line is guiding you THROUGH off-road terrain\n"
    "      (not alongside a road or back to a road)\n"
    "\n"
    "  If there is ANY tarmac or paved road visible ahead: use RULE 15 (FULL_THROTTLE)\n"
    "  If grass is just alongside a road: use RULE 4 (off-road return), NOT this rule.\n"
    "\n"
    "  Confirmed cross-country, path clear ahead, terrain is passable:\n"
    "  => OFFROAD_THROTTLE\n"
    "  Rock / tree / fence on the RIGHT, clear space left:\n"
    "  => OFFROAD_LEFT\n"
    "  Rock / tree / fence on the LEFT, clear space right:\n"
    "  => OFFROAD_RIGHT\n"
    "  Very rough terrain (rocks, steep bank, river, deep ruts):\n"
    "  => OFFROAD_CAREFUL"
)

if OLD_R13 in rules_str:
    rules_str = rules_str.replace(OLD_R13, NEW_R13, 1)
    print("Patched RULE 13")
else:
    print("WARNING: RULE 13 not found exactly -- trying partial match")
    if "CROSS COUNTRY / DIRT RACE EVENT" in rules_str:
        print("  Header found -- content may have changed. Skipping RULE 13 patch.")
    else:
        print("  RULE 13 not found at all")

# ══════════════════════════════════════════════════════════════════════════════
# 2. Add clarity to RULE 4 header -- road race vs cross-country distinction
# ══════════════════════════════════════════════════════════════════════════════
OLD_R4_HEADER = (
    "RULE 4 -- OFF ROAD IN A ROAD/STREET RACE  [grass/dirt under tyres]:\n"
    "  Applies when: grass, dirt, gravel or sand is clearly visible UNDER the car,\n"
    "  AND this is a Road Race or Street Scene event (NOT cross-country or dirt race).\n"
    "  Goal: SLOW DOWN \u2192 REALIGN \u2192 RETURN TO TARMAC \u2192 BUILD SPEED AGAIN."
)
NEW_R4_HEADER = (
    "RULE 4 -- OFF ROAD IN A ROAD/STREET RACE  [grass/dirt under tyres]:\n"
    "  Applies when: grass, dirt, gravel or sand is clearly visible UNDER the car,\n"
    "  AND a paved tarmac road is still visible nearby (to the side or ahead).\n"
    "  KEY DIFFERENCE FROM RULE 13: in RULE 4 the road is still VISIBLE beside or ahead of you.\n"
    "  Goal: SLOW DOWN \u2192 REALIGN \u2192 RETURN TO TARMAC \u2192 BUILD SPEED AGAIN."
)
if OLD_R4_HEADER in rules_str:
    rules_str = rules_str.replace(OLD_R4_HEADER, NEW_R4_HEADER, 1)
    print("Patched RULE 4 header with road-vs-offroad distinction")
else:
    print("WARNING: RULE 4 header not found")

cfg["decision_rules"] = rules_str.split("\n")

# ══════════════════════════════════════════════════════════════════════════════
# 3. Add hard OFFROAD constraint near the top of constraints
# ══════════════════════════════════════════════════════════════════════════════
OFFROAD_CONSTRAINT = (
    "* NEVER pick OFFROAD_THROTTLE, OFFROAD_LEFT, OFFROAD_RIGHT, or OFFROAD_CAREFUL "
    "during a ROAD RACE or STREET SCENE event. Those actions are ONLY for cross-country "
    "and dirt race events where the game explicitly sends you through rough terrain with "
    "no tarmac road. If you see tarmac ahead OR the event HUD says Road Race / Street "
    "Scene: pick FULL_THROTTLE (on road) or ROAD_RETURN_* (if off the road edge)."
)

# Insert right after the 3 forward-bias constraints (after index 3)
# Find a good insertion point: after "If the car is moving at any speed"
insert_idx = next(
    (i for i, c in enumerate(cfg["constraints"]) if "moving at any speed" in c),
    3
) + 1

cfg["constraints"].insert(insert_idx, OFFROAD_CONSTRAINT)
print(f"Inserted OFFROAD constraint at index {insert_idx}")
print(f"Constraints now: {len(cfg['constraints'])} items")

# ══════════════════════════════════════════════════════════════════════════════
# 4. Write + verify
# ══════════════════════════════════════════════════════════════════════════════
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\nconfig.json updated  ({p.stat().st_size:,} bytes)")
print(f"  decision_rules : {len(cfg['decision_rules'])} lines")
print(f"  constraints    : {len(cfg['constraints'])} items")
r = "\n".join(cfg["decision_rules"])
c = "\n".join(cfg["constraints"])
print(f"  RULE 13 explicit trigger: {'ALL of these are true' in r}")
print(f"  RULE 4 road visible note: {'road is still VISIBLE' in r}")
print(f"  OFFROAD constraint added: {'NEVER pick OFFROAD_THROTTLE' in c}")
