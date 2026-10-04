import math

import pygame

import config


def screen_x_for(position: float) -> float:
    progress = min(position, config.TRACK_LENGTH) / config.TRACK_LENGTH
    return config.START_X + progress * (config.FINISH_X - config.START_X)


class Car:
    def __init__(self, idle: pygame.Surface, accelerating: pygame.Surface,
                 lane_y: int, position: int) -> None:
        self.idle = idle
        self.accelerating = accelerating
        self.lane_y = lane_y
        self.visual_position = float(position)
        self.target_position = float(position)
        self.anim_time = 0.0

    @property
    def is_moving(self) -> bool:
        return self.visual_position < self.target_position

    def move_to(self, position: int) -> None:
        self.target_position = float(position)

    def snap_to(self, position: int) -> None:
        self.visual_position = self.target_position = float(position)

    def update(self, dt: float) -> None:
        self.anim_time += dt
        if self.is_moving:
            step = dt / config.CAR_SECONDS_PER_UNIT
            self.visual_position = min(self.visual_position + step, self.target_position)

    def draw(self, surface: pygame.Surface) -> None:
        sprite = self.accelerating if self.is_moving else self.idle
        shake = round(math.sin(self.anim_time * 60)) if self.is_moving else 0
        rect = sprite.get_rect(right=round(screen_x_for(self.visual_position)),
                               bottom=self.lane_y + shake)
        surface.blit(sprite, rect)
