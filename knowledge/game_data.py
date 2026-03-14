"""
MapleBot - Game Knowledge Database
Comprehensive data about MapleRoyals v62: training spots, monster data,
skill builds, and map information. Sourced from MapleRoyals wiki,
community guides, and Hidden-Street database.

This module serves as the bot's "memory" — it knows everything a veteran
MapleStory player would know, without needing to learn it from scratch.
"""


# =====================================================
# TRAINING SPOTS BY LEVEL — I/L MAGE OPTIMIZED
# Priority order within each level range.
# Each entry: (map_name, monsters, notes, exp_tier)
# exp_tier: S/A/B/C — based on community consensus
# =====================================================

TRAINING_SPOTS = [
    # === BEGINNER / 1ST JOB (1-30) ===
    {
        "level_min": 1, "level_max": 10,
        "map": "Maple Island",
        "monsters": ["Snail", "Blue Snail", "Shroom", "Stump"],
        "notes": "Complete Maple Island quests for fast early levels",
        "exp_tier": "A",
        "element_bonus": None,
    },
    {
        "level_min": 8, "level_max": 15,
        "map": "Ellinia: Dungeon, Southern Forest I",
        "monsters": ["Slime", "Green Slime"],
        "notes": "Good for new mages — close to Ellinia town",
        "exp_tier": "B",
        "element_bonus": None,
    },
    {
        "level_min": 10, "level_max": 20,
        "map": "Henesys Pig Farm",
        "monsters": ["Pig", "Ribbon Pig"],
        "notes": "Flat map, easy mobs, good for early grinding",
        "exp_tier": "A",
        "element_bonus": None,
    },
    {
        "level_min": 15, "level_max": 25,
        "map": "Kerning City Subway",
        "monsters": ["Bubbling", "Jr. Necki"],
        "notes": "Good density, easy to reach from Kerning",
        "exp_tier": "A",
        "element_bonus": None,
    },
    {
        "level_min": 21, "level_max": 30,
        "map": "Land of Wild Boar 2",
        "monsters": ["Wild Boar", "Iron Boar"],
        "notes": "Great mob density and EXP — top pick for 20s",
        "exp_tier": "S",
        "element_bonus": None,
    },
    {
        "level_min": 21, "level_max": 35,
        "map": "Kerning Party Quest (KPQ)",
        "monsters": ["Party Quest"],
        "notes": "Best EXP with a party — social and efficient",
        "exp_tier": "S",
        "element_bonus": None,
    },

    # === 2ND JOB (30-70) ===
    {
        "level_min": 30, "level_max": 50,
        "map": "Carnival Party Quest (CPQ)",
        "monsters": ["Party Quest"],
        "notes": "EXTREMELY fast — best in game for 30-50. Look for parties.",
        "exp_tier": "S",
        "element_bonus": None,
    },
    {
        "level_min": 35, "level_max": 50,
        "map": "Ludibrium Party Quest (LPQ)",
        "monsters": ["Party Quest"],
        "notes": "Alternative to CPQ — good with experienced party",
        "exp_tier": "A",
        "element_bonus": None,
    },
    {
        "level_min": 30, "level_max": 55,
        "map": "Ghost Ship 2 (GS2)",
        "monsters": ["Slimy", "Ghost Pirate"],
        "notes": "LIGHTNING WEAK — Thunderbolt melts these. Potion intensive!",
        "exp_tier": "S",
        "element_bonus": "lightning",
    },
    {
        "level_min": 35, "level_max": 50,
        "map": "Eos Tower: Retz Map",
        "monsters": ["Retz"],
        "notes": "Decent for I/L mages with Thunderbolt",
        "exp_tier": "B",
        "element_bonus": None,
    },
    {
        "level_min": 45, "level_max": 60,
        "map": "Ghost Ship 5",
        "monsters": ["Slimy", "Ghost Pirate"],
        "notes": "Less crowded alternative to GS2, same mobs",
        "exp_tier": "A",
        "element_bonus": "lightning",
    },
    {
        "level_min": 50, "level_max": 70,
        "map": "Forest of Golem",
        "monsters": ["Mixed Golem", "Dark Stone Golem"],
        "notes": "Good EXP + GFA 60% scroll drops ($$)",
        "exp_tier": "A",
        "element_bonus": None,
    },

    # === 3RD JOB (70-120) ===
    {
        "level_min": 62, "level_max": 80,
        "map": "Ghost Ship 2 (GS2) - revisit",
        "monsters": ["Slimy"],
        "notes": "Still great for I/L with Ice Strike — can one-shot with decent gear",
        "exp_tier": "A",
        "element_bonus": "lightning",
    },
    {
        "level_min": 70, "level_max": 85,
        "map": "Voodoos",
        "monsters": ["Voodoo"],
        "notes": "Good mesos + EXP. Heartstopper drops are valuable.",
        "exp_tier": "A",
        "element_bonus": None,
    },
    {
        "level_min": 75, "level_max": 95,
        "map": "Wolf Spider Cavern",
        "monsters": ["Wolf Spider"],
        "notes": "Popular training spot — great EXP/hr",
        "exp_tier": "S",
        "element_bonus": None,
    },
    {
        "level_min": 85, "level_max": 100,
        "map": "Himes",
        "monsters": ["Hime"],
        "notes": "Great solo or duo — ice mage friendly",
        "exp_tier": "A",
        "element_bonus": "ice",
    },
    {
        "level_min": 87, "level_max": 120,
        "map": "Galloperas",
        "monsters": ["Gallopera"],
        "notes": "Safe and consistent — slightly slower but chill",
        "exp_tier": "B",
        "element_bonus": None,
    },
    {
        "level_min": 100, "level_max": 120,
        "map": "Ulu Estate 2-3",
        "monsters": ["Ulu monster"],
        "notes": "Good for higher level 3rd job grind",
        "exp_tier": "A",
        "element_bonus": None,
    },
    {
        "level_min": 105, "level_max": 120,
        "map": "Leafre: Destroyed Dragon Nest",
        "monsters": ["Jr. Newtie"],
        "notes": "Solid EXP — need decent Magic Attack",
        "exp_tier": "A",
        "element_bonus": None,
    },
    {
        "level_min": 105, "level_max": 125,
        "map": "Singapore: Ulu City Center",
        "monsters": ["Petrifighter"],
        "notes": "AMAZING with ~1200+ Magic Attack to 1-shot. Top tier 3rd→4th job.",
        "exp_tier": "S",
        "element_bonus": None,
    },
    {
        "level_min": 108, "level_max": 130,
        "map": "Leafre: Dragon Nest Left Behind",
        "monsters": ["Skelegon", "Skelosaurus"],
        "notes": "Top 3 for EXP AND mesos. Endgame 3rd job grind.",
        "exp_tier": "S",
        "element_bonus": None,
    },

    # === 4TH JOB (120+) ===
    {
        "level_min": 120, "level_max": 140,
        "map": "Wolf Spider Cavern",
        "monsters": ["Wolf Spider"],
        "notes": "Still great post-4th job — Blizzard wrecks entire map",
        "exp_tier": "A",
        "element_bonus": None,
    },
    {
        "level_min": 120, "level_max": 150,
        "map": "Skelegon / Dragon Nest Left Behind",
        "monsters": ["Skelegon", "Skelosaurus"],
        "notes": "Blizzard + Chain Lightning tears through these",
        "exp_tier": "S",
        "element_bonus": None,
    },
    {
        "level_min": 135, "level_max": 200,
        "map": "Zakum",
        "monsters": ["Zakum"],
        "notes": "Boss — excellent EXP for all classes at 135+",
        "exp_tier": "S",
        "element_bonus": None,
    },
    {
        "level_min": 153, "level_max": 200,
        "map": "Temple of Time",
        "monsters": ["Lyka"],
        "notes": "WEAK TO ICE — mages can safe-spot Lyka easily",
        "exp_tier": "S",
        "element_bonus": "ice",
    },
    {
        "level_min": 153, "level_max": 200,
        "map": "Lionheart Castle (LHC)",
        "monsters": ["Various LHC mobs"],
        "notes": "Mages are EXCELLENT here — top tier endgame",
        "exp_tier": "S",
        "element_bonus": None,
    },
    {
        "level_min": 170, "level_max": 200,
        "map": "Reverse Golem (RG)",
        "monsters": ["Reverse Golem"],
        "notes": "I/L mages are particularly strong here at 170+",
        "exp_tier": "S",
        "element_bonus": None,
    },
]


# =====================================================
# SKILL BUILD — I/L MAGE (MapleRoyals v62)
# Priority order for skill point allocation per job
# =====================================================

SKILL_BUILD = {
    "1st_job": {
        "level_range": "8-30",
        "priority": [
            "Energy Bolt → 1 (initial attack)",
            "Improving MP Recovery → MAX",
            "Improving MaxMP Increase → MAX",
            "Magic Claw → MAX (main attack)",
            "Magic Guard → MAX (critical survivability)",
            "Magic Armor → MAX",
        ],
        "main_attack": "Magic Claw",
        "notes": "Magic Guard is essential — shifts damage from HP to MP",
    },
    "2nd_job": {
        "level_range": "30-70",
        "priority": [
            "Teleport → 1 (mobility — essential)",
            "Thunder Bolt → 1 (start leveling)",
            "Meditation → MAX (party buff, increases MA)",
            "Spell Booster → MAX (faster casting)",
            "Thunder Bolt → MAX (main AoE attack)",
            "Cold Beam → MAX (freeze utility)",
            "MP Eater → MAX (MP conservation)",
            "Slow → leftover",
        ],
        "main_attack": "Thunder Bolt",
        "notes": "Thunderbolt is your bread and butter for 30-70. Hits multiple mobs.",
    },
    "3rd_job": {
        "level_range": "70-120",
        "priority": [
            "Ice Strike → 1 (start using immediately)",
            "Elemental Amplification → MAX (damage boost)",
            "Ice Strike → MAX (main grinding skill 70-120)",
            "Seal → MAX or skip",
            "Element Composition → MAX",
            "Ifrit → MAX (summon for extra DPS)",
        ],
        "main_attack": "Ice Strike",
        "notes": "Ice Strike is your PRIMARY skill from 70-120. Freezes + AoE.",
    },
    "4th_job": {
        "level_range": "120-200",
        "priority": [
            "Blizzard → MAX (full-map ultimate — NO cooldown!)",
            "Chain Lightning → MAX (main skill for bossing + mobbing)",
            "Infinity → MAX (unlimited MP for 40s)",
            "Maple Warrior → MAX (party stat boost)",
            "Meteor Shower → MAX (fire ultimate)",
        ],
        "main_attack": "Blizzard / Chain Lightning",
        "notes": "Blizzard hits entire map with no cooldown — makes you a grinding GOD.",
    },
}


# =====================================================
# CHAT RESPONSES — Natural human-like replies
# Used when other players talk to the bot
# =====================================================

CHAT_RESPONSES = {
    # When someone asks you to change channel
    "cc_please": [
        "sry didnt see u, ill cc",
        "oh mb, ccing",
        "my bad, leaving",
        "didnt know someone was here, ccing",
        "ok going",
    ],
    # When someone asks if you're a bot
    "are_you_bot": [
        "lol no, just grinding",
        "nah, just watching youtube while grinding xd",
        "haha no, just half afk",
        "wut? no lol",
        "nah just chilling",
        "lol im just bad",
    ],
    # When someone says hi or greets
    "greeting": [
        "hey",
        "hi",
        "yo",
        "sup",
        "heya",
    ],
    # When someone asks about your level/class
    "about_me": [
        "just leveling my mage",
        "grinding i/l, trying to get to 4th job",
        "just a mage trying to level up lol",
    ],
    # Kill steal complaint
    "ks_complaint": [
        "oh sry didnt realize, ill move",
        "my bad, going to another channel",
        "sry about that",
        "oh mb",
    ],
    # General chat — keep it short
    "general": [
        "nice",
        "haha",
        "lol",
        "true",
        "gg",
        "yeah",
        "idk",
        "thx",
    ],
    # When someone offers party
    "party_invite": [
        "sure",
        "yeah ok",
        "yea inv me",
        "down",
    ],
    # When someone asks for trade
    "trade": [
        "nah im good thx",
        "no thanks",
        "im ok ty",
    ],
    # Farewell
    "farewell": [
        "cya",
        "bye",
        "peace",
        "gl",
        "later",
    ],
}


# Keywords that trigger each response category
CHAT_TRIGGERS = {
    "cc_please": ["cc", "cc pls", "cc please", "change channel", "ccpls", "cc plz", "my map"],
    "are_you_bot": ["bot?", "r u a bot", "are you a bot", "bot check", "u bot", "ur a bot", "macro"],
    "greeting": ["hi", "hello", "hey", "sup", "yo", "hii", "heya", "helo"],
    "about_me": ["what class", "what lvl", "what level", "ur class", "what job"],
    "ks_complaint": ["ks", "kill steal", "stop ks", "ur ksing", "ksing", "my channel", "i was here"],
    "party_invite": ["party?", "wanna party", "pt?", "want to party", "join pt"],
    "trade": ["trade?", "wanna trade", "buy", "sell"],
    "farewell": ["bye", "cya", "gl", "later", "peace", "bb"],
}


# =====================================================
# POTIONS — Know what pots to use at each level
# =====================================================

POTIONS = {
    "hp": [
        {"name": "Red Potion", "heal": 50, "cost": 50, "level_range": (1, 15)},
        {"name": "Orange Potion", "heal": 150, "cost": 200, "level_range": (15, 30)},
        {"name": "White Potion", "heal": 300, "cost": 500, "level_range": (25, 50)},
        {"name": "Unagi", "heal": 1000, "cost": 800, "level_range": (40, 80)},
        {"name": "Elixir", "heal": "50%", "cost": 4000, "level_range": (70, 200)},
        {"name": "Power Elixir", "heal": "100%", "cost": 10000, "level_range": (100, 200)},
    ],
    "mp": [
        {"name": "Blue Potion", "heal": 100, "cost": 200, "level_range": (1, 20)},
        {"name": "Mana Elixir", "heal": 300, "cost": 800, "level_range": (20, 50)},
        {"name": "Elixir", "heal": "50%", "cost": 4000, "level_range": (50, 200)},
        {"name": "Power Elixir", "heal": "100%", "cost": 10000, "level_range": (100, 200)},
    ],
}


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def get_training_spots(level, top_n=3):
    """Get the best training spots for a given level."""
    spots = [
        s for s in TRAINING_SPOTS
        if s["level_min"] <= level <= s["level_max"]
    ]
    # Sort by tier (S > A > B > C)
    tier_order = {"S": 0, "A": 1, "B": 2, "C": 3}
    spots.sort(key=lambda s: tier_order.get(s["exp_tier"], 99))
    return spots[:top_n]


def get_element_advantage_spots(level):
    """Get spots where I/L mage has elemental advantage."""
    return [
        s for s in TRAINING_SPOTS
        if s["level_min"] <= level <= s["level_max"]
        and s["element_bonus"] is not None
    ]


def get_chat_response(message):
    """
    Determine the best response to an incoming chat message.
    Returns (category, response) or (None, None) if no match.
    """
    import random
    msg_lower = message.lower().strip()

    for category, triggers in CHAT_TRIGGERS.items():
        for trigger in triggers:
            if trigger in msg_lower:
                responses = CHAT_RESPONSES.get(category, [])
                if responses:
                    return category, random.choice(responses)

    return None, None


def get_current_skill_info(level):
    """Get skill build info for current level."""
    if level < 30:
        return SKILL_BUILD["1st_job"]
    elif level < 70:
        return SKILL_BUILD["2nd_job"]
    elif level < 120:
        return SKILL_BUILD["3rd_job"]
    else:
        return SKILL_BUILD["4th_job"]


# =====================================================
# Quick test
# =====================================================
if __name__ == "__main__":
    print("=== Training Spots Test ===")
    for level in [10, 25, 40, 70, 100, 120, 150]:
        spots = get_training_spots(level)
        print(f"\nLevel {level}:")
        for s in spots:
            elem = f" [{s['element_bonus'].upper()} WEAK!]" if s['element_bonus'] else ""
            print(f"  [{s['exp_tier']}] {s['map']} — {', '.join(s['monsters'])}{elem}")

    print("\n=== Chat Response Test ===")
    test_msgs = ["cc pls", "are you a bot?", "hi", "stop ksing me", "wanna party?"]
    for msg in test_msgs:
        cat, resp = get_chat_response(msg)
        print(f"  '{msg}' → [{cat}] '{resp}'")

    print("\n=== Skill Build ===")
    info = get_current_skill_info(45)
    print(f"Level 45 ({info['level_range']}): Main attack = {info['main_attack']}")
