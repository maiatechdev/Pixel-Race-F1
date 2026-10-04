import math
import random
from dataclasses import dataclass

import pygame

import config

FLAG_DARK = (20, 20, 20)
FLAG_LIGHT = (240, 240, 240)
POLE_COLOR = (170, 170, 180)


@dataclass
class Confetti:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    size: int


class FinishCelebration:
    def __init__(self) -> None:
        self.started = False
        self.elapsed = 0.0
        self.pole_x = 0
        self.pole_bottom = 0
        self.confetti: list[Confetti] = []

    @property
    def done(self) -> bool:
        return self.started and self.elapsed >= config.FINISH_CELEBRATION_SECONDS

    def start(self, pole_x: int, pole_bottom: int) -> None:
        if self.started:
            return
        self.started = True
        self.elapsed = 0.0
        self.pole_x = pole_x
        self.pole_bottom = pole_bottom
        flag_top = pole_bottom - config.FLAG_POLE_HEIGHT
        self.confetti = [
            Confetti(
                x=pole_x + random.uniform(-40, 10),
                y=flag_top + random.uniform(0, 20),
                vx=random.uniform(-260, 120),
                vy=random.uniform(-420, -160),
                color=random.choice(config.CONFETTI_COLORS),
                size=random.choice((3, 4, 5)),
            )
            for _ in range(config.CONFETTI_COUNT)
        ]

    def update(self, dt: float) -> None:
        if not self.started:
            return
        self.elapsed += dt
        for piece in self.confetti:
            piece.vy += config.CONFETTI_GRAVITY * dt
            piece.vx *= 1 - min(1.0, config.CONFETTI_DRAG * dt)
            piece.x += piece.vx * dt
            piece.y += piece.vy * dt

    def draw(self, surface: pygame.Surface) -> None:
        if not self.started:
            return
        self._draw_flag(surface)
        for piece in self.confetti:
            if piece.y < config.HUD_TOP:
                pygame.draw.rect(surface, piece.color, (round(piece.x), round(piece.y), piece.size, piece.size))

    def _draw_flag(self, surface: pygame.Surface) -> None:
        top = self.pole_bottom - config.FLAG_POLE_HEIGHT
        pygame.draw.rect(surface, POLE_COLOR, (self.pole_x, top, 3, config.FLAG_POLE_HEIGHT))
        cell = config.FLAG_CELL
        for col in range(config.FLAG_COLUMNS):
            wave = round(math.sin(self.elapsed * config.FLAG_WAVE_SPEED + col * 0.9) * 3)
            x = self.pole_x - (col + 1) * cell
            for row in range(config.FLAG_ROWS):
                color = FLAG_DARK if (row + col) % 2 else FLAG_LIGHT
                pygame.draw.rect(surface, color, (x, top + 2 + row * cell + wave, cell, cell))
