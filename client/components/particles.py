import random
from dataclasses import dataclass

import pygame

import config
from components.car import Car

SMOKE = "smoke"
SPARK = "spark"
WHEEL_RADIUS = 10
FLOOR_OFFSET_X = 70
FLOOR_LIFT = 3


@dataclass
class Particle:
    kind: str
    x: float
    y: float
    vx: float
    vy: float
    life: float
    start_size: float
    end_size: float
    color: tuple[int, int, int]
    age: float = 0.0

    @property
    def progress(self) -> float:
        return min(1.0, self.age / self.life)


class ParticleSystem:
    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self.overlay = pygame.Surface((config.BASE_WIDTH, config.HUD_TOP), pygame.SRCALPHA)

    def emit_smoke(self, x: float, y: float, count: int, strength: float = 1.0) -> None:
        for _ in range(count):
            shade = random.randint(185, 225)
            self._add(Particle(
                kind=SMOKE,
                x=x + random.uniform(-3, 3),
                y=y + random.uniform(-2, 1),
                vx=random.uniform(-150, -60) * strength,
                vy=random.uniform(-35, -8) * strength,
                life=random.uniform(0.5, 0.9),
                start_size=random.uniform(3, 5),
                end_size=random.uniform(9, 14) * strength,
                color=(shade, shade, shade + 5),
            ))

    def emit_sparks(self, x: float, y: float, count: int) -> None:
        for _ in range(count):
            self._add(Particle(
                kind=SPARK,
                x=x + random.uniform(-8, 8),
                y=y,
                vx=random.uniform(-340, -170),
                vy=random.uniform(-90, -10),
                life=random.uniform(0.18, 0.4),
                start_size=2,
                end_size=1,
                color=random.choice(config.SPARK_COLORS),
            ))

    def _add(self, particle: Particle) -> None:
        if len(self.particles) < config.MAX_PARTICLES:
            self.particles.append(particle)

    def update(self, dt: float) -> None:
        for particle in self.particles:
            particle.age += dt
            if particle.kind == SPARK:
                particle.vy += config.SPARK_GRAVITY * dt
            else:
                particle.vx *= 1 - min(1.0, config.SMOKE_DRAG * dt)
                particle.vy *= 1 - min(1.0, config.SMOKE_DRAG * dt)
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
        self.particles = [p for p in self.particles if p.age < p.life]

    def draw_smoke(self, surface: pygame.Surface) -> None:
        self.overlay.fill((0, 0, 0, 0))
        for particle in self.particles:
            if particle.kind != SMOKE:
                continue
            t = particle.progress
            size = round(particle.start_size + (particle.end_size - particle.start_size) * t)
            alpha = round(config.SMOKE_MAX_ALPHA * (1 - t))
            rect = pygame.Rect(0, 0, size, size)
            rect.center = (round(particle.x), round(particle.y))
            pygame.draw.rect(self.overlay, (*particle.color, alpha), rect)
        surface.blit(self.overlay, (0, 0))

    def draw_sparks(self, surface: pygame.Surface) -> None:
        for particle in self.particles:
            if particle.kind != SPARK:
                continue
            head = (round(particle.x), round(particle.y))
            tail = (round(particle.x - particle.vx * config.SPARK_TRAIL_SECONDS),
                    round(particle.y - particle.vy * config.SPARK_TRAIL_SECONDS))
            pygame.draw.line(surface, particle.color, head, tail, 2 if particle.progress < 0.5 else 1)


class CarEffects:
    def __init__(self) -> None:
        self.was_moving = False
        self.smoke_timer = 0.0

    def update(self, dt: float, car: Car, particles: ParticleSystem) -> None:
        moving = car.is_moving
        body = car.body_rect()
        (rear_x, wheel_y), (front_x, _) = car.wheel_centers
        ground_y = body.y + wheel_y + WHEEL_RADIUS - 2
        rear = (body.x + rear_x, ground_y)
        floor = (body.x + FLOOR_OFFSET_X, body.bottom - FLOOR_LIFT)

        if moving and not self.was_moving:
            particles.emit_smoke(*rear, config.LAUNCH_SMOKE_COUNT, strength=1.3)
            particles.emit_sparks(*floor, config.LAUNCH_SPARK_COUNT)
        if moving:
            self.smoke_timer += dt
            while self.smoke_timer >= config.SMOKE_INTERVAL:
                self.smoke_timer -= config.SMOKE_INTERVAL
                particles.emit_smoke(*rear, 1, strength=0.8)
            if random.random() < config.SPARK_BURSTS_PER_SECOND * dt:
                particles.emit_sparks(*floor, random.randint(3, 6))
        if self.was_moving and not moving:
            particles.emit_smoke(*rear, config.BRAKE_SMOKE_COUNT, strength=0.6)
            particles.emit_smoke(body.x + front_x, ground_y, config.BRAKE_SMOKE_COUNT, strength=0.6)
        self.was_moving = moving
