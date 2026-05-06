"""Debug badge scoring for a specific player."""
import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from nba2k26_generator.nba_site_normalization import load_nba_site_rows
from nba2k26_generator.generator_cli import (
    compute_attributes, compute_tendencies, compute_badge_groups,
    compute_attribute_family_averages, as_float, remap, clamp,
    normalize_player_name_for_match, ATTRIBUTE_MIN,
)

rows = load_nba_site_rows('NBA Site data')
BADGES_TXT = os.path.join('Badges', 'NBA 2K26 Badges.txt')

targets = ['Gilgeous-Alexander', 'Giannis', 'Anthony Edwards', 'Dončić']

for name_part in targets:
    for r in rows:
        if name_part.lower() in str(r.get('player_name', '')).lower():
            tendencies = compute_tendencies(r)
            result = compute_attributes(r, tendencies, 'Player Roles', all_rows=rows, badges_txt_path=BADGES_TXT)
            attrs = result['attributes']
            
            # Check key raw data
            dunks_share = as_float(r, "dunks_share")
            name = r['player_name']
            pos = r['position']
            
            # Compute what Posterizer score would be
            tendency_map = {normalize_player_name_for_match(t.name): float(t.final) for t in tendencies}
            def na(name):
                return clamp(remap(float(attrs.get(name, ATTRIBUTE_MIN)), 25.0, 95.0, 0.0, 100.0), 0.0, 100.0)
            def td(name):
                return float(tendency_map.get(normalize_player_name_for_match(name), 0.0))
            def ts(name, lo, hi):
                return clamp(remap(td(name), lo, hi, 0.0, 100.0), 0.0, 100.0)
            
            # Posterizer formula
            poster_gate = dunks_share >= 0.02
            if poster_gate:
                poster_score = (
                    0.35 * na("Driving Dunk") + 0.20 * na("Vertical") +
                    0.10 * na("Strength") + 0.20 * ts("Driving Dunk", 10, 55) +
                    0.15 * ts("Flashy Dunk", 5, 40)
                )
            else:
                poster_score = -1
            
            # Rise Up formula  
            is_big = "C" in pos.upper() or "PF" in pos.upper()
            rise_gate = (is_big and dunks_share >= 0.03) or dunks_share >= 0.08
            if rise_gate:
                rise_score = (
                    0.40 * na("Standing Dunk") + 0.20 * na("Strength") +
                    0.25 * ts("Standing Dunk", 10, 60) + 0.15 * na("Vertical")
                )
            else:
                rise_score = -1
            
            # Aerial Wizard
            aw_gate = dunks_share >= 0.02 or is_big
            if aw_gate:
                aw_score = (
                    0.22 * na("Driving Dunk") + 0.13 * na("Standing Dunk") +
                    0.20 * na("Vertical") + 0.25 * ts("Alley-Oop", 5, 55) +
                    0.20 * ts("Putback", 5, 50)
                )
            else:
                aw_score = -1
                
            print(f'{name} ({pos}) dunks_share={dunks_share:.3f} is_big={is_big}')
            print(f'  DrDnk={attrs["Driving Dunk"]} StDnk={attrs["Standing Dunk"]} Vert={attrs["Vertical"]} Str={attrs["Strength"]}')
            print(f'  tend DrDnk={td("Driving Dunk"):.0f} FlashyDnk={td("Flashy Dunk"):.0f} StDnk={td("Standing Dunk"):.0f} AlleyOop={td("Alley-Oop"):.0f} Putback={td("Putback"):.0f}')
            print(f'  Posterizer:     gate={poster_gate}, score={poster_score:.1f}')
            print(f'  Rise Up:        gate={rise_gate}, score={rise_score:.1f}')
            print(f'  Aerial Wizard:  gate={aw_gate}, score={aw_score:.1f}')
            
            # Check badge output
            badges = result.get('badges', {})
            all_badges = []
            for sb in badges.values():
                for b in sb:
                    all_badges.append(f'{b["name"]}({b["value"][0]}{b["score"]:.0f})')
            has_poster = any('Posterizer' in b for b in all_badges)
            has_rise = any('Rise Up' in b for b in all_badges)
            has_aw = any('Aerial Wizard' in b for b in all_badges)
            print(f'  In output: Posterizer={has_poster} Rise Up={has_rise} Aerial Wizard={has_aw}')
            print(f'  Total badges: {len(all_badges)}')
            print()
            break
