import sys, os
sys.path.insert(0, '.')
from nba2k26_generator.generator_cli import load_badge_catalog
c = load_badge_catalog('Badges/NBA 2K26 Badges.txt')
for section, badges in c.items():
    names = [b["name"] for b in badges]
    print(f"{section} ({len(names)}): {names}")
