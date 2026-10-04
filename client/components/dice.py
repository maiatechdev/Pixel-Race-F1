import random

import pygame

import config

SIZE = 44
PIP = 6

PIPS = {
    1: [(1, 1)],
    2: [(0, 0), (2, 2)],
    3: [(0, 0), (1, 1), (2, 2)],
    4: [(0, 0), (2, 0), (0, 2), (2, 2)],
    5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)],
    6: [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2)],
}


class Dice:
    def __init__(self, value: int | None) -> None:
        self.value = value
        self.rolling = False
        self._elapsed = 0.0
        self._face_timer = 0.0
        self._result: int | None = None
        self._value_before_roll = value

    def start_roll(self) -> None:
        self._value_before_roll = self.value
        self.rolling = True
        self._elapsed = 0.0
        self._result = None

    def set_result(self, value: int) -> None:
        self._result = value

    def cancel(self) -> None:
        self.rolling = False
        self._result = None
        self.value = self._value_before_roll

    @property
    def done(self) -> bool:
        return not self.rolling

    def update(self, dt: float) -> None:
        if not self.rolling:
            return
        self._elapsed += dt
        self._face_timer += dt
        if self._face_timer >= config.DICE_FACE_INTERVAL:
            self._face_timer = 0.0
            self.value = random.randint(1, 6)
        if self._elapsed >= config.DICE_ROLL_DURATION and self._result is not None:
            self.value = self._result
            self.rolling = False

    def draw(self, surface: pygame.Surface, center: tuple[int, int]) -> None:
        rect = pygame.Rect(0, 0, SIZE, SIZE)
        rect.center = center
        if self.rolling:
            rect.y -= 2 * (int(self._elapsed * 20) % 2)
        pygame.draw.rect(surface, (20, 20, 20), rect.inflate(4, 4))
        pygame.draw.rect(surface, (245, 245, 245), rect)
        if self.value is None:
            return
        cell = SIZE // 3
        for gx, gy in PIPS[self.value]:
            pip = pygame.Rect(0, 0, PIP, PIP)
            pip.center = (rect.x + cell * gx + cell // 2, rect.y + cell * gy + cell // 2)
            pygame.draw.rect(surface, (20, 20, 20), pip)
