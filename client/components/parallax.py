import pygame


class ParallaxLayer:
    def __init__(self, image: pygame.Surface, y: int, speed_factor: float) -> None:
        self.image = image
        self.y = y
        self.speed_factor = speed_factor
        self.offset = 0.0

    def update(self, dt: float, scroll_speed: float) -> None:
        self.offset = (self.offset + scroll_speed * self.speed_factor * dt) % self.image.get_width()

    def draw(self, surface: pygame.Surface) -> None:
        width = self.image.get_width()
        x = -int(self.offset)
        while x < surface.get_width():
            surface.blit(self.image, (x, self.y))
            x += width
