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


class PropLayer:
    def __init__(self, props: list[tuple[pygame.Surface, int]], bottom_y: int,
                 period: int, speed_factor: float) -> None:
        self.props = props
        self.bottom_y = bottom_y
        self.period = period
        self.speed_factor = speed_factor
        self.offset = 0.0

    def update(self, dt: float, scroll_speed: float) -> None:
        self.offset = (self.offset + scroll_speed * self.speed_factor * dt) % self.period

    def draw(self, surface: pygame.Surface) -> None:
        for image, x in self.props:
            screen_x = (x - int(self.offset)) % self.period
            for candidate_x in (screen_x, screen_x - self.period):
                if candidate_x + image.get_width() > 0 and candidate_x < surface.get_width():
                    surface.blit(image, image.get_rect(left=candidate_x, bottom=self.bottom_y))
