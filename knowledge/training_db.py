"""
MapleBot — Training Knowledge Base
Complete database of MapleStory v62 training areas, monsters, and progression.
Built from MapleRoyals guides, wiki data, and community resources.

Sources:
  - MapleRoyals forum guides (royals.ms)
  - MapleStory Wiki (maplestory.wiki/GMS/62)
  - StrategyWiki MapleStory
  - Community YouTube guides
"""

# ============================================================
# Monster Database
# ============================================================
MONSTERS = {
    # --- Maple Island ---
    "snail":             {"level": 1,  "hp": 8,     "exp": 3,   "element": "neutral"},
    "blue_snail":        {"level": 2,  "hp": 15,    "exp": 4,   "element": "neutral"},
    "shroom":            {"level": 3,  "hp": 20,    "exp": 5,   "element": "neutral"},
    "orange_mushroom":   {"level": 6,  "hp": 40,    "exp": 8,   "element": "neutral"},
    "pig":               {"level": 8,  "hp": 55,    "exp": 12,  "element": "neutral"},
    "ribbon_pig":        {"level": 10, "hp": 80,    "exp": 15,  "element": "neutral"},
    
    # --- Victoria Island Low Level ---
    "slime":             {"level": 5,  "hp": 30,    "exp": 6,   "element": "neutral"},
    "green_mushroom":    {"level": 8,  "hp": 50,    "exp": 10,  "element": "neutral"},
    "bubbling":          {"level": 10, "hp": 125,   "exp": 17,  "element": "neutral"},
    "stump":             {"level": 10, "hp": 100,   "exp": 15,  "element": "neutral"},
    "dark_stump":        {"level": 15, "hp": 200,   "exp": 22,  "element": "neutral"},
    "axe_stump":         {"level": 18, "hp": 300,   "exp": 28,  "element": "neutral"},
    
    # --- Kerning City Subway ---
    "stirge":            {"level": 18, "hp": 250,   "exp": 25,  "element": "neutral"},
    "jr_wraith":         {"level": 23, "hp": 600,   "exp": 43,  "element": "holy_weak"},
    "wraith":            {"level": 43, "hp": 2800,  "exp": 120, "element": "holy_weak"},
    "shade":             {"level": 53, "hp": 4500,  "exp": 175, "element": "holy_weak"},
    
    # --- Ant Tunnel ---
    "horny_mushroom":    {"level": 20, "hp": 450,   "exp": 35,  "element": "neutral"},
    "zombie_mushroom":   {"level": 25, "hp": 800,   "exp": 50,  "element": "holy_weak"},
    "evil_eye":          {"level": 24, "hp": 700,   "exp": 48,  "element": "neutral"},
    "curse_eye":         {"level": 28, "hp": 1000,  "exp": 60,  "element": "neutral"},
    
    # --- Henesys ---
    "jr_necki":          {"level": 13, "hp": 150,   "exp": 18,  "element": "neutral"},
    "mixed_golem":       {"level": 25, "hp": 850,   "exp": 52,  "element": "neutral"},
    "stone_golem":       {"level": 22, "hp": 600,   "exp": 42,  "element": "neutral"},
    "dark_stone_golem":  {"level": 28, "hp": 1050,  "exp": 65,  "element": "neutral"},
    
    # --- Sleepywood ---
    "copper_drake":      {"level": 35, "hp": 1800,  "exp": 88,  "element": "neutral"},
    "dark_drake":        {"level": 40, "hp": 2400,  "exp": 110, "element": "neutral"},
    "red_drake":         {"level": 45, "hp": 3000,  "exp": 140, "element": "ice_weak"},
    "tauromacis":        {"level": 35, "hp": 1900,  "exp": 90,  "element": "neutral"},
    "wild_boar":         {"level": 28, "hp": 1100,  "exp": 62,  "element": "neutral"},
    
    # --- Kerning Square ---
    "cd":                {"level": 33, "hp": 1500,  "exp": 80,  "element": "neutral"},
    "mannequin":         {"level": 28, "hp": 1000,  "exp": 58,  "element": "neutral"},
    
    # --- Ninja Castle ---
    "genin":             {"level": 36, "hp": 2000,  "exp": 95,  "element": "neutral"},
    "chunin":            {"level": 42, "hp": 2600,  "exp": 115, "element": "neutral"},
    
    # --- NLC ---
    "rotting_skeleton":  {"level": 22, "hp": 500,   "exp": 40,  "element": "holy_weak"},
    
    # --- Ludibrium ---
    "teddy":             {"level": 30, "hp": 1200,  "exp": 70,  "element": "neutral"},
    "panda_teddy":       {"level": 35, "hp": 1700,  "exp": 85,  "element": "neutral"},
    "master_chronos":    {"level": 45, "hp": 3200,  "exp": 145, "element": "neutral"},
    "toy_trojan":        {"level": 33, "hp": 1500,  "exp": 78,  "element": "neutral"},
}


# ============================================================
# Training Progression Guide (Level → Best Maps)
# ============================================================
TRAINING_GUIDE = {
    # (min_level, max_level): [map options in priority order]
    (1, 10):   [
        {"map": "maple_island", "monsters": ["snail", "blue_snail", "shroom", "orange_mushroom"],
         "notes": "Complete Maple Island quests for fast levels"},
    ],
    (10, 15):  [
        {"map": "slime_cave", "monsters": ["slime"],
         "notes": "Ellinia Slime Tree — excellent spawn rate"},
        {"map": "henesys_hunting_ground", "monsters": ["slime", "orange_mushroom"],
         "notes": "Henesys Hunting Ground I-III"},
    ],
    (15, 20):  [
        {"map": "pig_beach", "monsters": ["pig", "ribbon_pig"],
         "notes": "Pig Beach near Lith Harbor"},
        {"map": "subway_line1_area1", "monsters": ["bubbling"],
         "notes": "Kerning Subway — decent for mages with magic claw"},
    ],
    (20, 25):  [
        {"map": "ant_tunnel", "monsters": ["horny_mushroom", "zombie_mushroom"],
         "notes": "Ant Tunnel III — accept quest for 14,400 EXP! Best for mages"},
        {"map": "henesys_hunting_ground", "monsters": ["green_mushroom", "orange_mushroom"],
         "notes": "HHG III — easy mobs, good spawn"},
        {"map": "kpq", "monsters": [],
         "notes": "Kerning Party Quest (KPQ) — great group EXP Lv21-30"},
    ],
    (25, 30):  [
        {"map": "ant_tunnel", "monsters": ["horny_mushroom", "evil_eye", "curse_eye"],
         "notes": "Continue Ant Tunnel — should 2-3 hit with maxed Magic Claw"},
        {"map": "kerning_square", "monsters": ["mannequin", "cd"],
         "notes": "Kerning Square Mall — CDs at floor 3 are excellent"},
        {"map": "kpq", "monsters": [],
         "notes": "KPQ still viable until 30"},
        {"map": "nlc_haunted", "monsters": ["rotting_skeleton"],
         "notes": "NLC Haunted House — rotting skeletons, holy-weak"},
    ],
    (30, 40):  [
        {"map": "ninja_castle", "monsters": ["genin"],
         "notes": "Inside the Castle Gate — Genins, stay until 40"},
        {"map": "kerning_square", "monsters": ["cd"],
         "notes": "CDs — flat map, great for mobbing mages"},
        {"map": "cpq", "monsters": [],
         "notes": "Carnival Party Quest (CPQ) Lv30-51 — coins + EXP"},
        {"map": "wild_boar_land", "monsters": ["wild_boar"],
         "notes": "Wild Boar Land near Perion"},
        {"map": "ludibrium", "monsters": ["teddy", "panda_teddy"],
         "notes": "Teddies in KFT/Ludi area"},
    ],
    (40, 50):  [
        {"map": "cpq", "monsters": [],
         "notes": "CPQ — best group EXP, earn mesos from coins"},
        {"map": "ninja_castle", "monsters": ["chunin"],
         "notes": "Chunins if strong enough"},
        {"map": "wild_boar_land", "monsters": ["wild_boar"],
         "notes": "Still viable with strong mobbing"},
    ],
    (50, 70):  [
        {"map": "silent_swamp", "monsters": ["copper_drake"],
         "notes": "Silent Swamp in Sleepywood — BEST solo spot to 70"},
        {"map": "sleepywood", "monsters": ["dark_drake", "red_drake"],
         "notes": "Dark/Red Drakes — deeper in Sleepywood"},
        {"map": "lmpq", "monsters": [],
         "notes": "Ludibrium Party Quest (LMPQ) — great group EXP"},
    ],
}


# ============================================================
# Monster Visual Signatures (for detector)
# ============================================================
# HSV color ranges that identify each monster type
MONSTER_VISUALS = {
    "bubbling": {
        "primary_color": "bright_blue",
        "hsv_lower": [95, 80, 140],
        "hsv_upper": [120, 255, 255],
        "min_area": 200,
        "max_area": 5000,
        "shape": "blob",  # Round blob shape
    },
    "slime": {
        "primary_color": "green",
        "hsv_lower": [35, 80, 100],
        "hsv_upper": [75, 255, 255],
        "min_area": 200,
        "max_area": 4000,
        "shape": "blob",
    },
    "orange_mushroom": {
        "primary_color": "orange",
        "hsv_lower": [10, 100, 150],
        "hsv_upper": [20, 255, 255],
        "min_area": 300,
        "max_area": 5000,
        "shape": "mushroom",
    },
    "pig": {
        "primary_color": "pink",
        "hsv_lower": [150, 30, 150],
        "hsv_upper": [175, 180, 255],
        "min_area": 400,
        "max_area": 6000,
        "shape": "pig",
    },
    "horny_mushroom": {
        "primary_color": "dark_purple",
        "hsv_lower": [130, 50, 50],
        "hsv_upper": [160, 200, 200],
        "min_area": 300,
        "max_area": 5000,
        "shape": "mushroom",
    },
    "jr_wraith": {
        "primary_color": "dark_gray",
        "hsv_lower": [0, 0, 30],
        "hsv_upper": [180, 40, 120],
        "min_area": 300,
        "max_area": 5000,
        "shape": "ghost",
    },
}


# ============================================================
# Helper functions
# ============================================================

def get_training_maps(level: int):
    """Get recommended training maps for a given level."""
    results = []
    for (min_lv, max_lv), maps in TRAINING_GUIDE.items():
        if min_lv <= level <= max_lv:
            results.extend(maps)
    return results


def get_monster_info(name: str):
    """Get monster stats by name."""
    key = name.lower().replace(" ", "_").replace(".", "")
    return MONSTERS.get(key)


def get_monster_visuals(name: str):
    """Get visual detection parameters for a monster."""
    key = name.lower().replace(" ", "_").replace(".", "")
    return MONSTER_VISUALS.get(key)


def suggest_next_map(current_level: int, current_map: str = None):
    """Suggest the best training map for current level."""
    maps = get_training_maps(current_level)
    if not maps:
        return None
    # Return first recommendation (highest priority)
    return maps[0]


# ============================================================
# Quick reference
# ============================================================
if __name__ == "__main__":
    print("=== MapleBot Training Knowledge Base ===\n")
    
    for (min_lv, max_lv), maps in sorted(TRAINING_GUIDE.items()):
        print(f"Level {min_lv}-{max_lv}:")
        for m in maps:
            monsters = ", ".join(m["monsters"]) if m["monsters"] else "PQ mobs"
            print(f"  📍 {m['map']}: {monsters}")
            print(f"     {m['notes']}")
        print()
    
    print(f"\n{len(MONSTERS)} monsters in database")
    print(f"{len(MONSTER_VISUALS)} monsters with visual signatures")
