from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "assets_originais"
OUTPUT_DIR = ROOT / "assets"

NEUTRAL_TOLERANCE = 14
TONE_TOLERANCE = 16
BORDER_BAND = 12
HOLE_MIN_AREA = 300
HOLE_MIN_TONE_SHARE = 0.15
EDGE_CLEANUP_PASSES = 2
SPECK_MAX_SHARE = 0.01
ALPHA_THRESHOLD = 128

CAR_BODY_WIDTH = 150
WHEEL_FRAME_COUNT = 8

SIMPLE_ASSETS = {
    "helmets/red.png": ("height", 40),
    "helmets/blue.png": ("height", 40),
    "circuit/lamp_post.png": ("height", 120),
    "circuit/control_tower.png": ("height", 150),
    "circuit/starting_lights.png": ("height", 90),
    "barriers/tire_wall.png": ("height", 40),
    "barriers/concrete_wall.png": ("height", 32),
    "track/grass.png": ("height", 40),
    "background/mountains.png": ("width", 960),
    "background/trees.png": ("width", 960),
    "background/grandstand.png": ("width", 960),
}

CARS = {
    "red": ("cars/red/idle.png", "cars/red/accelerate.png"),
    "blue": ("cars/blue/idle.png", "cars/blue/accelerate.png"),
}


def brightness(pixel: tuple[int, int, int]) -> int:
    return sum(pixel) // 3


def is_neutral(pixel: tuple[int, int, int]) -> bool:
    return max(pixel) - min(pixel) <= NEUTRAL_TOLERANCE


def checker_tones(pixels: list, width: int, height: int) -> tuple[int, int]:
    levels = []
    for y in range(height):
        band = range(width) if y < BORDER_BAND or y >= height - BORDER_BAND else (
            list(range(BORDER_BAND)) + list(range(width - BORDER_BAND, width)))
        for x in band:
            pixel = pixels[y * width + x]
            if is_neutral(pixel):
                levels.append(brightness(pixel))
    levels.sort()
    low_end = levels[len(levels) * 5 // 100]
    high_end = levels[len(levels) * 95 // 100]
    split = (low_end + high_end) // 2
    dark = [level for level in levels if level < split] or [low_end]
    light = [level for level in levels if level >= split] or [high_end]
    return dark[len(dark) // 2], light[len(light) // 2]


def neighbors(index: int, width: int, height: int):
    x, y = index % width, index // width
    if x > 0:
        yield index - 1
    if x < width - 1:
        yield index + 1
    if y > 0:
        yield index - width
    if y < height - 1:
        yield index + width


def connected_components(mask: bytearray, width: int, height: int):
    visited = bytearray(len(mask))
    for start in range(len(mask)):
        if not mask[start] or visited[start]:
            continue
        component = []
        touches_border = False
        queue = deque([start])
        visited[start] = 1
        while queue:
            index = queue.popleft()
            component.append(index)
            x, y = index % width, index // width
            if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                touches_border = True
            for neighbor in neighbors(index, width, height):
                if mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    queue.append(neighbor)
        yield component, touches_border


def remove_specks(background: bytearray, width: int, height: int) -> None:
    opaque = bytearray(0 if value else 1 for value in background)
    islands = [component for component, _ in connected_components(opaque, width, height)]
    if not islands:
        return
    largest = max(len(island) for island in islands)
    for island in islands:
        if len(island) < largest * SPECK_MAX_SHARE:
            for index in island:
                background[index] = 1


def remove_checkerboard(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = list(rgb.get_flattened_data())
    dark_tone, light_tone = checker_tones(pixels, width, height)

    def tone_of(pixel) -> int:
        if not is_neutral(pixel):
            return 0
        level = brightness(pixel)
        if abs(level - dark_tone) <= TONE_TOLERANCE:
            return 1
        if abs(level - light_tone) <= TONE_TOLERANCE:
            return 2
        return 0

    tones = bytearray(tone_of(pixel) for pixel in pixels)
    background = bytearray(len(pixels))

    for component, touches_border in connected_components(tones, width, height):
        dark_share = sum(1 for index in component if tones[index] == 1) / len(component)
        is_checker_hole = (len(component) >= HOLE_MIN_AREA
                           and HOLE_MIN_TONE_SHARE <= dark_share <= 1 - HOLE_MIN_TONE_SHARE)
        if touches_border or is_checker_hole:
            for index in component:
                background[index] = 1

    low_limit = dark_tone - TONE_TOLERANCE
    high_limit = light_tone + TONE_TOLERANCE
    for _ in range(EDGE_CLEANUP_PASSES):
        edge = [index for index in range(len(pixels))
                if not background[index]
                and is_neutral(pixels[index])
                and low_limit <= brightness(pixels[index]) <= high_limit
                and any(background[n] for n in neighbors(index, width, height))]
        for index in edge:
            background[index] = 1

    remove_specks(background, width, height)

    rgba = rgb.convert("RGBA")
    rgba.putdata([(r, g, b, 0) if background[i] else (r, g, b, 255)
                  for i, (r, g, b) in enumerate(pixels)])
    return rgba


def shrink(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    premultiplied = image.convert("RGBa").resize(size, Image.Resampling.BOX)
    result = premultiplied.convert("RGBA")
    result.putdata([(r, g, b, 255) if a >= ALPHA_THRESHOLD else (0, 0, 0, 0)
                    for r, g, b, a in result.get_flattened_data()])
    return result


def target_size(size: tuple[int, int], rule: tuple[str, int]) -> tuple[int, int]:
    width, height = size
    kind, value = rule
    if kind == "height":
        return max(1, round(width * value / height)), value
    return value, max(1, round(height * value / width))


def save(image: Image.Image, relative_path: str) -> None:
    path = OUTPUT_DIR / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    print(f"{relative_path}: {image.width}x{image.height}")


def load_clean(relative_path: str) -> Image.Image:
    return remove_checkerboard(Image.open(SOURCE_DIR / relative_path))


def process_simple_assets() -> None:
    for relative_path, rule in SIMPLE_ASSETS.items():
        clean = load_clean(relative_path)
        cropped = clean.crop(clean.getbbox())
        save(shrink(cropped, target_size(cropped.size, rule)), relative_path)


def process_cars() -> float:
    scale = 1.0
    for idle_path, accelerate_path in CARS.values():
        idle, accelerate = load_clean(idle_path), load_clean(accelerate_path)
        idle_box, accelerate_box = idle.getbbox(), accelerate.getbbox()
        box = (min(idle_box[0], accelerate_box[0]), min(idle_box[1], accelerate_box[1]),
               max(idle_box[2], accelerate_box[2]), max(idle_box[3], accelerate_box[3]))
        scale = CAR_BODY_WIDTH / (idle_box[2] - idle_box[0])
        size = (round((box[2] - box[0]) * scale), round((box[3] - box[1]) * scale))
        save(shrink(idle.crop(box), size), idle_path)
        save(shrink(accelerate.crop(box), size), accelerate_path)
    return scale


def first_opaque_run(image: Image.Image) -> tuple[int, int]:
    alpha = image.getchannel("A")
    rows = [any(alpha.crop((0, y, image.width, y + 1)).get_flattened_data()) for y in range(image.height)]
    top = rows.index(True)
    bottom = top
    while bottom < len(rows) and rows[bottom]:
        bottom += 1
    return top, bottom


def process_wheels(scale: float) -> None:
    sheet = load_clean("wheels/wheel_sheet.png")
    frame_width = sheet.width / WHEEL_FRAME_COUNT
    wheels = []
    for number in range(WHEEL_FRAME_COUNT):
        column = sheet.crop((round(number * frame_width), 0,
                             round((number + 1) * frame_width), sheet.height))
        top, bottom = first_opaque_run(column)
        wheel = column.crop((0, top, column.width, bottom))
        wheels.append(wheel.crop(wheel.getbbox()))
    diameter = max(1, round(max(wheels[0].size) * scale))
    for number, wheel in enumerate(wheels, start=1):
        save(shrink(wheel, (diameter, diameter)), f"wheels/frame_{number}.png")


def main() -> None:
    process_simple_assets()
    scale = process_cars()
    process_wheels(scale)


if __name__ == "__main__":
    main()
