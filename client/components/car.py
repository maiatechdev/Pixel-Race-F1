import math

import pygame

import config
from assets import load_image


def screen_x_for(position: float) -> float:
    progress = min(position, config.TRACK_LENGTH) / config.TRACK_LENGTH
    return config.START_X + progress * (config.FINISH_X - config.START_X)


def load_wheel_frames() -> list[pygame.Surface]:
    return [load_image(f"wheels/frame_{number}.png")
            for number in range(1, config.WHEEL_FRAME_COUNT + 1)]


class Car:
    def __init__(self, color: str, wheel_frames: list[pygame.Surface],
                 lane_y: int, position: int) -> None:
        self.idle = load_image(f"cars/{color}/idle.png")
        self.accelerating = load_image(f"cars/{color}/accelerate.png")
        sprite_info = config.CAR_SPRITES[color]
        self.wheel_centers = sprite_info["wheel_centers"]
        self.accelerate_offset_x = sprite_info["accelerate_offset_x"]
        self.wheel_frames = wheel_frames
        self.lane_y = lane_y
        self.visual_position = float(position)
        self.target_position = float(position)
        self.anim_time = 0.0
        self.wheel_spin = 0.0
        self.wheel_angle = 0.0

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

        spin_change = dt / config.WHEEL_SPIN_UP_SECONDS
        if self.is_moving:
            self.wheel_spin = min(1.0, self.wheel_spin + spin_change)
        else:
            self.wheel_spin = max(0.0, self.wheel_spin - spin_change)
        self.wheel_angle = (self.wheel_angle
                            + self.wheel_spin * config.WHEEL_MAX_DEGREES_PER_SECOND * dt) % 360

    def body_rect(self) -> pygame.Rect:
        return self.idle.get_rect(right=round(screen_x_for(self.visual_position)), bottom=self.lane_y)

    def draw(self, surface: pygame.Surface) -> None:
        moving = self.is_moving
        shake = round(math.sin(self.anim_time * 60)) if moving else 0
        body = self.body_rect().move(0, shake)
        if moving:
            surface.blit(self.accelerating, body.move(self.accelerate_offset_x, 0))
        else:
            surface.blit(self.idle, body)
        self._draw_wheels(surface, body)

    def _draw_wheels(self, surface: pygame.Surface, body: pygame.Rect) -> None:
        frame_index = round(self.wheel_spin * (len(self.wheel_frames) - 1))
        wheel = pygame.transform.rotate(self.wheel_frames[frame_index], -self.wheel_angle)
        for center_x, center_y in self.wheel_centers:
            surface.blit(wheel, wheel.get_rect(center=(body.x + center_x, body.y + center_y)))
