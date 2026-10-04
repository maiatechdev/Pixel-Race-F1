import pygame

from config import ASSETS_DIR


def load_image(relative_path: str) -> pygame.Surface:
    path = ASSETS_DIR / relative_path
    return pygame.image.load(str(path)).convert_alpha()


def scale_to_height(image: pygame.Surface, height: int) -> pygame.Surface:
    width = round(image.get_width() * height / image.get_height())
    return pygame.transform.scale(image, (width, height))



_fonts: dict[int, pygame.font.Font] = {}


def pixel_font(size: int) -> pygame.font.Font:
    if size not in _fonts:
        _fonts[size] = pygame.font.Font(str(ASSETS_DIR / "fonts" / "PressStart2P-Regular.ttf"), size)
    return _fonts[size]


def truncate(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[:max_chars - 1].rstrip() + "."
