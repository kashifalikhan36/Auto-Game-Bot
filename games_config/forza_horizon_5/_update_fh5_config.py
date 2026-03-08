"""Update FH5 config.json: add scene_analysis_prompt, concise rules/constraints."""
import json, pathlib

cfg_path = pathlib.Path("games_config/forza_horizon_5/config.json")
d = json.loads(cfg_path.read_text(encoding="utf-8"))

# ── Scene analysis prompt (sent to Groq vision → returns JSON) ──────────────
d["scene_analysis_prompt"] = """Analyse this Forza Horizon 5 screenshot and return ONLY a JSON object with these exact fields:
{
  "event": "road_race|cross_country|street_scene|drag|drift_zone|speed_trap|speed_zone|freeroam|menu",
  "car_on_road": true or false,
  "car_speed": "stopped|slow|medium|fast",
  "car_state": "normal|stuck|spinning",
  "road_ahead": "straight|curve_left|curve_right|hairpin_left|hairpin_right|none",
  "racing_line": "green|orange|red|none",
  "hazard_type": "none|wall|tree|barrier|traffic",
  "hazard_direction": "none|ahead|left|right",
  "surface": "tarmac|offroad",
  "menu_visible": true or false,
  "overtake_possible": true or false
}
Rules:
- event: read from HUD banner/text. Use "freeroam" if no event text is visible.
- car_speed: stopped=0 km/h, slow<60, medium<120, fast>=120
- car_state: stuck=pressed against obstacle with no movement; spinning=facing wrong direction
- racing_line: coloured line painted on road surface (green=go fast, orange=lift off, red=brake hard). "none" if not visible.
- surface: tarmac=paved road; offroad=dirt/grass/gravel/sand
- hazard: object that could cause a collision within the next 2 seconds
Return ONLY the JSON object. No markdown, no explanation."""

# ── Concise decision rules ───────────────────────────────────────────────────
d["decision_rules"] = [
    "Apply rules TOP to BOTTOM. Use the FIRST rule whose conditions match the scene JSON.",
    "",
    "R1  MENU:      menu_visible=true OR event=menu  ->  DO_NOTHING",
    "",
    "R2  STUCK:     car_state=stuck AND car_speed=stopped",
    "               hazard_direction=left   ->  UNSTICK_REVERSE_RIGHT",
    "               hazard_direction=right  ->  UNSTICK_REVERSE_LEFT",
    "               else                   ->  UNSTICK_REVERSE",
    "",
    "R3  SPIN:      car_state=spinning AND car_speed=stopped",
    "               ->  SPIN_RECOVER_LEFT or SPIN_RECOVER_RIGHT (opposite of spin direction)",
    "",
    "R4  OFFROAD RECOVERY (road_race / street_scene / freeroam only):",
    "               car_on_road=false AND event IN [road_race, street_scene, freeroam]",
    "               tarmac close (partly visible)  ->  ROAD_NUDGE_LEFT / ROAD_NUDGE_RIGHT",
    "               tarmac moderate distance       ->  ROAD_RETURN_LEFT / ROAD_RETURN_RIGHT",
    "               tarmac far / deep off-road     ->  ROAD_RECOVER_LEFT / ROAD_RECOVER_RIGHT",
    "               Steer TOWARD the road. After returning: THROTTLE_LIGHT for 2 frames.",
    "",
    "R5  COLLISION: hazard_type!=none AND hazard_direction=ahead AND car_speed!=stopped",
    "               ->  BRAKE_HARD, or SWERVE_LEFT / SWERVE_RIGHT (away from hazard side)",
    "",
    "R6  DRIFT ZONE: event=drift_zone",
    "               ->  HANDBRAKE_DRIFT_LEFT or HANDBRAKE_DRIFT_RIGHT (into corner)",
    "",
    "R7  DRAG RACE: event=drag",
    "               ->  first frame: DRAG_RACE_LAUNCH; then FULL_THROTTLE",
    "",
    "R8  SPEED TRAP: event IN [speed_trap, speed_zone]",
    "               ->  SPEED_TRAP_BLAST",
    "",
    "R9  HAIRPIN:   road_ahead=hairpin_left   ->  CORNER_BRAKE_EXIT_LEFT",
    "               road_ahead=hairpin_right  ->  CORNER_BRAKE_EXIT_RIGHT",
    "",
    "R10 RED LINE:  racing_line=red AND road_ahead=curve_left   ->  BRAKE_HEAVY then CORNER_APEX_LEFT",
    "               racing_line=red AND road_ahead=curve_right  ->  BRAKE_HEAVY then CORNER_APEX_RIGHT",
    "",
    "R11 ORANGE:    racing_line=orange AND road_ahead=curve_left   ->  BRAKE_MEDIUM or CORNER_LEFT_MEDIUM",
    "               racing_line=orange AND road_ahead=curve_right  ->  BRAKE_MEDIUM or CORNER_RIGHT_MEDIUM",
    "",
    "R12 GREEN:     racing_line=green AND road_ahead=curve_left    ->  ACCEL_LEFT_GENTLE",
    "               racing_line=green AND road_ahead=curve_right   ->  ACCEL_RIGHT_GENTLE",
    "",
    "R13 CROSS-COUNTRY: event=cross_country",
    "               road_ahead=straight    ->  OFFROAD_THROTTLE",
    "               road_ahead=curve_left  ->  OFFROAD_LEFT",
    "               road_ahead=curve_right ->  OFFROAD_RIGHT",
    "               car_state=stuck        ->  UNSTICK_REVERSE",
    "",
    "R14 DEFAULT:   ->  FULL_THROTTLE  (straight road on tarmac, no hazard — ~80% of frames)",
]

# ── Concise hard constraints ─────────────────────────────────────────────────
d["constraints"] = [
    "- NEVER use REWIND or REWIND_HOLD under any circumstance.",
    "- DEFAULT is FULL_THROTTLE on any straight tarmac road with no hazard.",
    "- NEVER use reverse/recovery actions unless car_speed=stopped.",
    "- NEVER use OFFROAD_* actions during road_race or street_scene on tarmac.",
    "- NEVER alternate NUDGE_LEFT and NUDGE_RIGHT on consecutive frames (causes oscillation).",
    "- BRAKE before a corner apex — never during the apex.",
    "- After any UNSTICK_* action: pick THROTTLE_LIGHT for the next 2 frames.",
    "- If the same action appears 4+ times in recent_actions: pick a different action.",
]

# ── Concise situation checklist ──────────────────────────────────────────────
d["situation_checklist"] = [
    "Scene data is provided as JSON above. Apply the decision rules to the JSON fields and output ONE action name.",
]

# ── Concise game context ─────────────────────────────────────────────────────
d["game_context"] = (
    "Forza Horizon 5 — open-world racing. "
    "Controls: W=throttle, S=brake/reverse, A=steer left, D=steer right, Space=handbrake. "
    "The scene is pre-analysed by a vision model into structured JSON each frame. "
    "Your job: map the JSON scene to exactly ONE named action using the decision rules. "
    "Goal: complete races cleanly and fast. Default on clear straight road: FULL_THROTTLE."
)

cfg_path.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
print("FH5 config updated successfully.")
print(f"  decision_rules lines   : {len(d['decision_rules'])}")
print(f"  constraints            : {len(d['constraints'])}")
print(f"  situation_checklist    : {len(d['situation_checklist'])}")
print(f"  scene_analysis_prompt  : {len(d['scene_analysis_prompt'])} chars")
