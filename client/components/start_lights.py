import pygame

import config


def bulb_rect(center: tuple[int, int]) -> pygame.Rect:
    rect = pygame.Rect(0, 0, config.GANTRY_LIGHT_SIZE, config.GANTRY_LIGHT_SIZE)
    rect.center = center
    return rect


def with_lights_off(gantry: pygame.Surface) -> pygame.Surface:
    unlit = gantry.copy()
    for center in config.GANTRY_LIGHT_CENTERS:
        rect = bulb_rect(center)
        for x in range(rect.left, rect.right):
            for y in range(rect.top, rect.bottom):
                r, g, b, a = unlit.get_at((x, y))
                if a and r > g + 40:
                    unlit.set_at((x, y), (r // 7 + 12, g // 4, b // 4, a))
    return unlit


class StartLights:
    def __init__(self, gantry: pygame.Surface) -> None:
        self.lit_image = gantry
        self.unlit_image = with_lights_off(gantry)
        self.started = False
        self.elapsed = 0.0

    @property
    def lights_out_time(self) -> float:
        return len(config.GANTRY_LIGHT_CENTERS) * config.START_LIGHT_INTERVAL + config.START_HOLD_SECONDS

    @property
    def lit_count(self) -> int:
        if not self.started or self.elapsed >= self.lights_out_time:
            return 0
        return min(len(config.GANTRY_LIGHT_CENTERS), int(self.elapsed / config.START_LIGHT_INTERVAL) + 1)

    @property
    def holding_race(self) -> bool:
        return self.started and self.elapsed < self.lights_out_time

    @property
    def showing_go(self) -> bool:
        return (self.started
                and self.lights_out_time <= self.elapsed < self.lights_out_time + config.GO_DISPLAY_SECONDS)

    def start(self) -> None:
        if not self.started:
            self.started = True
            self.elapsed = 0.0

    def update(self, dt: float) -> None:
        if self.started:
            self.elapsed += dt

    def draw(self, surface: pygame.Surface, topleft: tuple[int, int]) -> None:
        surface.blit(self.unlit_image, topleft)
        for center in config.GANTRY_LIGHT_CENTERS[:self.lit_count]:
            rect = bulb_rect(center)
            surface.blit(self.lit_image, rect.move(topleft), area=rect)
