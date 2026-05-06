import sys, os
sys.path.insert(0, '.')
from nba2k26_generator.nba_site_normalization import load_nba_site_rows
from nba2k26_generator.generator_cli import (
    compute_attributes, compute_tendencies, compute_attribute_family_averages,
    compute_overall_rating, ATTRIBUTE_FAMILIES,
)

rows = load_nba_site_rows('NBA Site data')
BADGES_TXT = os.path.join('Badges', 'NBA 2K26 Badges.txt')


def weighted(pairs):
    num = sum(v * w for v, w in pairs)
    den = sum(w for _, w in pairs)
    return num / den if den else 0


def clamp(v, lo=25, hi=99):
    return max(lo, min(hi, v))


def two_k_scale(raw):
    if raw >= 88:
        return min(99, raw + 5 + min(3, (raw - 88) * 0.4))
    if raw >= 78:
        return raw + 5
    if raw >= 65:
        return raw + 4
    if raw >= 50:
        return raw + 3
    return raw + 2


players = [
    'Gilgeous-Alexander',
    'Stephen Curry',
    'Giannis',
    'Wembanyama',
    'Anthony Edwards',
    'Jokic',
    'LeBron James',
    'Alex Caruso',
    'Dorian Finney-Smith',
    'Jalen Brunson',
]

print(f"{'Player':<28} {'Pos':<5} | {'Off':>4} {'Def':>4} {'Phy':>4} | {'OVR':>4} | bOVR")
print("-" * 72)

for name_part in players:
    for r in rows:
        if name_part.lower() in str(r.get('player_name', '')).lower():
            tendencies = compute_tendencies(r)
            bundle = compute_attributes(r, tendencies, 'Player Roles', all_rows=rows,
                                        badges_txt_path=BADGES_TXT)
            attrs = bundle['attributes']
            fs = bundle['family_scores']
            backend_ovr = bundle.get('ovr', 0)
            pos = r.get('position', '')
            name = r.get('player_name', '')

            finishing = fs.get('Finishing', 0)
            shooting = fs.get('Shooting', 0)
            playmaking = fs.get('Playmaking', 0)
            defense_fam = fs.get('Defense', 0)
            physical_fam = fs.get('Physical', 0)

            a = lambda k: float(attrs.get(k, 0))
            spd = a('Speed'); agi = a('Agility'); stren = a('Strength'); vert = a('Vertical')
            stl = a('Steal'); blk = a('Block'); intDef = a('Interior Defense')
            perDef = a('Perimeter Defense'); dreb = a('Defensive Rebound')
            passPerc = a('Pass Perception'); passAcc = a('Pass Accuracy')
            passVision = a('Pass Vision'); passIq = a('Pass IQ')
            shotIq = a('Shot IQ'); helpDefIq = a('Help Defense IQ')
            defCons = a('Defensive Consistency'); swb = a('Speed with Ball')
            handle = a('Ball Handle'); three = a('Three-Point Shot')
            mid = a('Mid-Range Shot'); driveDunk = a('Driving Dunk')
            layup = a('Driving Layup'); ft = a('Free Throw')
            stamina = a('Stamina'); postCtrl = a('Post Control')
            closeShot = a('Close Shot'); postHook = a('Post Hook')
            postFade = a('Post Fade')

            pos_upper = pos.upper()
            if 'C' in pos_upper or 'PF' in pos_upper:
                bucket = 'big'
            elif 'SF' in pos_upper:
                bucket = 'wing'
            else:
                bucket = 'guard'

            if bucket == 'guard':
                offRaw = weighted([(playmaking,0.3),(shooting,0.27),(finishing,0.13),(handle,0.1),(swb,0.1),(three,0.1)])
                creator = weighted([(playmaking,0.3),(handle,0.2),(swb,0.12),(passVision,0.14),(passAcc,0.12),(shotIq,0.12)])
                scorer = weighted([(shooting,0.34),(three,0.16),(mid,0.12),(finishing,0.18),(layup,0.1),(ft,0.1)])
                offBonus = min(8, max(0,creator-78)*0.35 + max(0,scorer-78)*0.25)
                offFloor = max(playmaking-1, creator-2, scorer-3, shooting-1)
                defRaw = weighted([(defense_fam,0.45),(perDef,0.2),(stl,0.15),(passPerc,0.1),(agi,0.1)])
                defFloor = max(defense_fam-1, weighted([(perDef,0.4),(stl,0.22),(passPerc,0.2),(helpDefIq,0.18)])-2)
                defBonus = 0
                phyRaw = weighted([(physical_fam,0.45),(spd,0.2),(agi,0.2),(stamina,0.15)])
            elif bucket == 'wing':
                offRaw = weighted([(shooting,0.24),(finishing,0.2),(playmaking,0.24),(mid,0.09),(three,0.09),(layup,0.08),(shotIq,0.06)])
                wingCreator = weighted([(playmaking,0.32),(handle,0.14),(swb,0.1),(passVision,0.16),(passAcc,0.12),(passIq,0.08),(shotIq,0.08)])
                wingScorer = weighted([(shooting,0.26),(finishing,0.2),(mid,0.12),(three,0.12),(layup,0.1),(ft,0.08),(shotIq,0.12)])
                offBonus = min(9, max(0,wingScorer-77)*0.34 + max(0,wingCreator-78)*0.33)
                offFloor = max(wingScorer-1, wingCreator-1, shooting-1, playmaking+1, finishing-1, shotIq-4)
                defRaw = weighted([(defense_fam,0.3),(perDef,0.18),(intDef,0.14),(stl,0.1),(blk,0.08),(passPerc,0.08),(helpDefIq,0.07),(defCons,0.05)])
                wingDI = weighted([(perDef,0.24),(intDef,0.2),(stl,0.12),(blk,0.08),(passPerc,0.12),(helpDefIq,0.14),(defCons,0.1)])
                defBonus = min(5, max(0,wingDI-74)*0.25 + max(0,defCons-75)*0.12)
                wingAF = weighted([(helpDefIq,0.36),(defCons,0.28),(perDef,0.2),(passPerc,0.16)])-1
                defFloor = max(defense_fam-1, wingDI-1, wingAF)
                phyRaw = weighted([(physical_fam,0.45),(spd,0.15),(agi,0.15),(stren,0.15),(vert,0.1)])
            else:
                offRaw = weighted([(finishing,0.24),(shooting,0.2),(playmaking,0.18),(driveDunk,0.1),(layup,0.08),(postCtrl,0.1),(closeShot,0.1)])
                postScoring = weighted([(finishing,0.24),(postCtrl,0.15),(closeShot,0.14),(postHook,0.1),(postFade,0.08),(shotIq,0.12),(shooting,0.1),(playmaking,0.07)])
                bigCreator = weighted([(playmaking,0.32),(passVision,0.2),(passAcc,0.16),(passIq,0.12),(shotIq,0.1),(handle,0.1)])
                offBonus = min(10, max(0,postScoring-77)*0.28 + max(0,bigCreator-79)*0.34 + max(0,shooting-78)*0.24)
                offFloor = max(postScoring-1, finishing-1, bigCreator-2, playmaking-1, shooting-2, shotIq-4)
                defRaw = weighted([(defense_fam,0.42),(intDef,0.17),(blk,0.14),(dreb,0.1),(perDef,0.07),(passPerc,0.1)])
                defFloor = max(defense_fam-1, weighted([(intDef,0.33),(blk,0.22),(dreb,0.18),(helpDefIq,0.14),(defCons,0.13)])-2)
                defBonus = 0
                phyRaw = weighted([(physical_fam,0.42),(stren,0.22),(vert,0.12),(spd,0.12),(agi,0.12)])

            offBase = round(clamp(max(offRaw + offBonus, offFloor)))
            defBase = round(clamp(max(defRaw + defBonus, defFloor)))
            phyBase = round(clamp(phyRaw))

            off = round(clamp(two_k_scale(offBase)))
            defe_card = round(clamp(two_k_scale(defBase)))
            phy_card = round(clamp(two_k_scale(phyBase)))

            if bucket == 'guard':
                ovrRaw = weighted([(off,0.55),(defe_card,0.12),(phy_card,0.33)])
                impact = min(8, max(0,off-88)*0.7 + max(0,phy_card-82)*0.3 + max(0,off-93)*0.5)
                pfloor = max(off-2, playmaking-2, shooting-2)
            elif bucket == 'wing':
                ovrRaw = weighted([(off,0.40),(defe_card,0.32),(phy_card,0.28)])
                impact = min(8, max(0,off-83)*0.5 + max(0,defe_card-80)*0.5 + max(0,phy_card-80)*0.3)
                pfloor = max(off-2, defe_card-3, phy_card-3)
            else:
                ovrRaw = weighted([(off,0.38),(defe_card,0.34),(phy_card,0.28)])
                impact = min(8, max(0,off-80)*0.55 + max(0,defe_card-78)*0.5 + max(0,phy_card-78)*0.35)
                pfloor = max(off-2, defe_card-3, phy_card-3)

            ovr_final = round(clamp(max(ovrRaw + impact, pfloor, backend_ovr)))

            print(f"{name:<28} {pos:<5} | {off:>4} {defe_card:>4} {phy_card:>4} | {ovr_final:>4} | {backend_ovr}")
            break
