"""
Kerning City Subway Line 1 <Area 1>
Map ID: 10301000

Monsters: Bubbling (Level 10, 125 HP, 17 EXP) — 64 spawns
Navigation: 3-4 platforms connected by ladders

Platform Layout (approximate pixel Y positions from top of client area):
  ┌──────────────────────────────────────────┐
  │  ╔═══════════════════════════╗  Top      │
  │  ║  Platform 3  (y ≈ 160)   ║           │
  │  ╚═══════════════════════════╝           │
  │          │ ladder │                       │
  │  ╔═══════════════════════════════╗       │
  │  ║  Platform 2  (y ≈ 280)       ║       │
  │  ╚═══════════════════════════════╝       │
  │          │ ladder │                       │
  │  ╔═══════════════════════════════════╗   │
  │  ║  Platform 1 / Ground  (y ≈ 430)  ║   │
  │  ╚═══════════════════════════════════╝   │
  │      [rails/tracks at bottom]            │
  └──────────────────────────────────────────┘

Entry: From Subway Ticketing Booth (left portal)
Exit: To Line 1 Area 2 (right portal)
"""

MAP_ID = 10301000
MAP_NAME = "Kerning City Subway Line 1 <Area 1>"

# Monster info
MONSTER = {
    "name": "Bubbling",
    "level": 10,
    "hp": 125,
    "exp": 17,
    "speed": 10,
    "spawn_count": 64,
    "element": "neutral",
}

# Platforms (approximate Y ranges in client-area pixels)
# These are calibrated from screenshot analysis
PLATFORMS = [
    {"name": "ground",    "y_min": 400, "y_max": 460, "x_min": 30,  "x_max": 800},
    {"name": "platform1", "y_min": 260, "y_max": 320, "x_min": 200, "x_max": 750},
    {"name": "platform2", "y_min": 160, "y_max": 210, "x_min": 300, "x_max": 700},
    {"name": "platform3", "y_min": 80,  "y_max": 130, "x_min": 350, "x_max": 650},
]

# Ladders/Ropes (approximate X positions)
LADDERS = [
    {"x": 230, "y_top": 260, "y_bottom": 430, "connects": ("ground", "platform1")},
    {"x": 400, "y_top": 160, "y_bottom": 310, "connects": ("platform1", "platform2")},
]

# Portals
PORTALS = [
    {"name": "exit_left",  "x": 30,  "y": 430, "destination": "Subway Ticketing Booth"},
    {"name": "exit_right", "x": 780, "y": 430, "destination": "Line 1 Area 2"},
]

# Patrol routes for botting
PATROL_ROUTES = {
    # Simple ground patrol: walk right → left → repeat
    "ground_simple": [
        ("walk_right", 4.0),
        ("attack", None),
        ("loot", None),
        ("walk_left", 4.0),
        ("attack", None),
        ("loot", None),
    ],
    # Multi-platform: ground → ladder up → platform1 → ladder down
    "multi_platform": [
        ("walk_right", 2.0),
        ("attack", None),
        ("climb_up", "ladder_0"),
        ("walk_right", 3.0),
        ("attack", None),
        ("walk_left", 3.0),
        ("attack", None),
        ("climb_down", "ladder_0"),
        ("walk_left", 2.0),
        ("loot", None),
    ],
}


def get_platform_for_y(y):
    """Return which platform a Y coordinate is on."""
    for p in PLATFORMS:
        if p["y_min"] <= y <= p["y_max"]:
            return p["name"]
    return "unknown"


def get_nearest_ladder(x, y, direction="up"):
    """Find the nearest ladder to climb."""
    best = None
    best_dist = float('inf')
    for ladder in LADDERS:
        dx = abs(ladder["x"] - x)
        if direction == "up":
            if y > ladder["y_top"]:
                if dx < best_dist:
                    best_dist = dx
                    best = ladder
        else:
            if y < ladder["y_bottom"]:
                if dx < best_dist:
                    best_dist = dx
                    best = ladder
    return best
