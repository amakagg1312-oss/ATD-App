import json, subprocess, sys

# Get ML output for Stephen Curry
result = subprocess.run(
    [sys.executable, '-m', 'nba2k26_generator.generator_cli', '--player', 'Stephen Curry', '--season', '2025-26', '--json'],
    capture_output=True, text=True, cwd='D:\\\\project'
)
lines = [l for l in result.stdout.strip().split(chr(10)) if l.startswith('{')]
data = json.loads(lines[0])
ml_attrs = data['profile']['attributes']

# Committee values for Stephen Curry
committee = {
    'driving_layup': 92, 'standing_dunk': 40, 'driving_dunk': 55, 'close_shot': 92,
    'mid_range_shot': 92, 'three_point_shot': 95, 'free_throw': 92, 'post_hook': 55,
    'post_fade': 40, 'post_control': 58, 'draw_foul': 92, 'shot_iq': 88,
    'ball_handle': 92, 'speed_with_ball': 94, 'hands': 78, 'pass_accuracy': 88,
    'pass_iq': 92, 'pass_vision': 90, 'offensive_consistency': 92, 'interior_defense': 60,
    'perimeter_defense': 72, 'steal': 70, 'block': 51, 'offensive_rebound': 42,
    'defensive_rebound': 58, 'help_defense_iq': 74, 'pass_perception': 70,
    'defensive_consistency': 72, 'speed': 88, 'agility': 90, 'strength': 60,
    'vertical': 82, 'stamina': 92, 'intangibles': 25, 'hustle': 90,
}

print(f"{'Attribute':<25s} | {'ML':>4s} | {'Committee':>10s} | {'Diff':>5s} | {'11+ Higher?':>12s} | {'Corrected?':>10s}")
print("-" * 80)

corrected_count = 0
total_11plus = 0
for attr_name, committee_val in committee.items():
    ml_val = ml_attrs.get(attr_name)
    if ml_val is not None:
        diff = committee_val - ml_val
        is_11plus = diff >= 11
        if is_11plus:
            total_11plus += 1
        was_corrected = (ml_val == committee_val) if is_11plus else (ml_val != committee_val or diff < 11)
        if is_11plus and ml_val == committee_val:
            corrected_count += 1
        print(f"{attr_name:<25s} | {ml_val:>4d} | {committee_val:>10d} | {diff:>+5d} | {'YES' if is_11plus else '':>12s} | {'CORRECTED' if (is_11plus and ml_val == committee_val) else ('NO!' if (is_11plus and ml_val != committee_val) else 'N/A'):>10s}")

print(f"\nTotal attributes where committee is 11+ higher: {total_11plus}")
print(f"Successfully corrected: {corrected_count}")
print(f"NOT corrected: {total_11plus - corrected_count}")
