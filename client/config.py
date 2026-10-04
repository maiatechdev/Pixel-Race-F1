from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

BASE_WIDTH = 960
BASE_HEIGHT = 540
WINDOW_SCALE = 1
FPS = 60

TRACK_LENGTH = 30

BACKDROP_HEIGHT = 300
TRACK_TOP = BACKDROP_HEIGHT
TRACK_BOTTOM = 450
HUD_TOP = TRACK_BOTTOM

LANE_RED_Y = 345
LANE_BLUE_Y = 425

START_X = 140
FINISH_X = 900

WHEEL_FRAME_COUNT = 8
WHEEL_SPIN_UP_SECONDS = 0.4
WHEEL_MAX_DEGREES_PER_SECOND = 900

CAR_SPRITES = {
    "red": {"wheel_centers": ((21, 26), (120, 26)), "accelerate_offset_x": -4},
    "blue": {"wheel_centers": ((21, 26), (120, 26)), "accelerate_offset_x": -2},
}

SCROLL_SPEED = 260
PARALLAX_TRACK = 1.0

SKY_HEIGHT = 320
PARALLAX_SKY = 0.02
BACKGROUND_LAYERS = (
    ("background/mountains.png", 200, 0.06),
    ("background/trees.png", 245, 0.15),
    ("background/grandstand.png", 300, 0.3),
)

TRACKSIDE_BOTTOM = 300
TRACKSIDE_PERIOD = 1440
PARALLAX_TRACKSIDE = 0.6
TRACKSIDE_PROPS = (
    ("circuit/lamp_post.png", 60),
    ("circuit/control_tower.png", 520),
    ("circuit/lamp_post.png", 820),
    ("circuit/lamp_post.png", 1180),
)

GANTRY_POST_OFFSET_X = 14
GANTRY_OVERHANG = 6

DICE_ROLL_DURATION = 0.7
DICE_FACE_INTERVAL = 0.07
CAR_SECONDS_PER_UNIT = 0.18

COLOR_HUD_BG = (20, 20, 32)
COLOR_HUD_BORDER = (240, 240, 240)
COLOR_TEXT = (240, 240, 240)
COLOR_TEXT_DIM = (130, 130, 150)
COLOR_RED = (220, 40, 40)
COLOR_BLUE = (40, 90, 220)
COLOR_YELLOW = (250, 210, 40)
COLOR_LANE_LINE = (230, 230, 230)
COLOR_CURB_RED = (200, 30, 30)
COLOR_CURB_WHITE = (235, 235, 235)
