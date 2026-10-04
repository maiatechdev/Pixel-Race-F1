import pygame

from config import ASSETS_DIR


def load_image(relative_path: str) -> pygame.Surface:
    path = ASSETS_DIR / relative_path
    return pygame.image.load(str(path)).convert_alpha()


def scale_to_height(image: pygame.Surface, height: int) -> pygame.Surface:
    width = round(image.get_width() * height / image.get_height())
    return pygame.transform.scale(image, (width, height))

