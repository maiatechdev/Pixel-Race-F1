import pygame

import config
from assets import load_image, scale_to_height, scale_to_width
from components.car import Car, screen_x_for
from components.dice import Dice
from components.hud import Hud, draw_text
from components.parallax import ParallaxLayer
from mock_game import PLAYER_1, PLAYER_2, MockGame

PLAYER_COLORS = {PLAYER_1: config.COLOR_RED, PLAYER_2: config.COLOR_BLUE}
CURB_HEIGHT = 8
CURB_SEGMENT = 24
CHECKER = 8


class RaceScreen:
    def __init__(self, game: MockGame) -> None:
        self.game = game
        self.phase = "IDLE"
        self.moving_player: int | None = None
        self.message = ""

        state = game.get_state()
        self.cars = {
            PLAYER_1: Car(self._car_image("cars/red/idle.png"),
                          self._car_image("cars/red/accelerate.png"),
                          config.LANE_RED_Y, state.players[PLAYER_1].position),
            PLAYER_2: Car(self._car_image("cars/blue/idle.png"),
                          self._car_image("cars/blue/accelerate.png"),
                          config.LANE_BLUE_Y, state.players[PLAYER_2].position),
        }
        self.shown_positions = {pid: p.position for pid, p in state.players.items()}

        self.backdrop = ParallaxLayer(
            scale_to_height(load_image("background/city_panorama.png"), config.BACKDROP_HEIGHT),
            y=0, speed_factor=config.PARALLAX_BACKDROP)
        track_height = config.TRACK_BOTTOM - config.TRACK_TOP
        self.asphalt = ParallaxLayer(
            scale_to_height(load_image("track/asphalt.png"), track_height),
            y=config.TRACK_TOP, speed_factor=config.PARALLAX_TRACK)
        self.track_offset = 0.0

        helmets = {
            PLAYER_1: scale_to_height(load_image("helmets/red.png"), config.HELMET_SIZE),
            PLAYER_2: scale_to_height(load_image("helmets/blue.png"), config.HELMET_SIZE),
        }
        self.hud = Hud(helmets)
        self.dice = Dice(state.last_dice)
        self.font_title = pygame.font.Font(None, 64)
        self.font = pygame.font.Font(None, 28)

    @staticmethod
    def _car_image(path: str) -> pygame.Surface:
        return scale_to_width(load_image(path), config.CAR_WIDTH)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self._request_roll()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hud.button_rect.collidepoint(event.pos):
                self._request_roll()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            if self.game.get_state().status == "FINISHED" and self.phase == "IDLE":
                self._restart()

    def _can_roll(self) -> bool:
        return self.phase == "IDLE" and self.game.get_state().status == "RUNNING"

    def _request_roll(self) -> None:
        if not self._can_roll():
            return
        player_id = self.game.get_state().current_turn
        self.dice.start_roll()
        result = self.game.roll_dice(player_id)
        if not result.ok:
            self.dice.rolling = False
            self.message = result.error or ""
            return
        self.message = ""
        self.dice.set_result(result.dice)
        self.moving_player = player_id
        self.phase = "ROLLING"

    def _restart(self) -> None:
        self.game.reset()
        state = self.game.get_state()
        for pid, car in self.cars.items():
            car.snap_to(state.players[pid].position)
        self.shown_positions = {pid: p.position for pid, p in state.players.items()}
        self.dice = Dice(state.last_dice)

    def update(self, dt: float) -> None:
        state = self.game.get_state()
        self.dice.update(dt)

        if self.phase == "ROLLING" and self.dice.done:
            pid = self.moving_player
            self.cars[pid].move_to(state.players[pid].position)
            self.phase = "MOVING"

        for car in self.cars.values():
            car.update(dt)

        if self.phase == "MOVING" and not self.cars[self.moving_player].is_moving:
            pid = self.moving_player
            self.shown_positions[pid] = state.players[pid].position
            self.moving_player = None
            self.phase = "IDLE"

        scroll = config.SCROLL_SPEED if self.phase == "MOVING" else 0.0
        self.backdrop.update(dt, scroll)
        self.asphalt.update(dt, scroll)
        self.track_offset = self.asphalt.offset

    def draw(self, surface: pygame.Surface) -> None:
        self.backdrop.draw(surface)
        self.asphalt.draw(surface)
        self._draw_track_markings(surface)
        self.cars[PLAYER_1].draw(surface)
        self.cars[PLAYER_2].draw(surface)
        self._draw_hud(surface)
        if self.game.get_state().status == "FINISHED" and self.phase == "IDLE":
            self._draw_finish_overlay(surface)

    def _draw_track_markings(self, surface: pygame.Surface) -> None:
        offset = int(self.track_offset)
        for y in (config.TRACK_TOP, config.TRACK_BOTTOM - CURB_HEIGHT):
            for i, x in enumerate(range(-offset % (CURB_SEGMENT * 2) - CURB_SEGMENT * 2,
                                        config.BASE_WIDTH, CURB_SEGMENT)):
                color = config.COLOR_CURB_RED if i % 2 == 0 else config.COLOR_CURB_WHITE
                pygame.draw.rect(surface, color, (x, y, CURB_SEGMENT, CURB_HEIGHT))

        lane_y = (config.LANE_RED_Y + config.LANE_BLUE_Y) // 2 - 12
        for x in range(-offset % 48 - 48, config.BASE_WIDTH, 48):
            pygame.draw.rect(surface, config.COLOR_LANE_LINE, (x, lane_y, 24, 3))

        track_inner_top = config.TRACK_TOP + CURB_HEIGHT
        track_inner_h = config.TRACK_BOTTOM - CURB_HEIGHT - track_inner_top
        start_x = round(screen_x_for(0))
        pygame.draw.rect(surface, config.COLOR_LANE_LINE, (start_x, track_inner_top, 3, track_inner_h))
        finish_x = round(screen_x_for(config.TRACK_LENGTH))
        for row in range(track_inner_h // CHECKER + 1):
            for col in range(2):
                color = (20, 20, 20) if (row + col) % 2 else (240, 240, 240)
                pygame.draw.rect(surface, color, (finish_x + col * CHECKER,
                                                  track_inner_top + row * CHECKER, CHECKER, CHECKER))

    def _draw_hud(self, surface: pygame.Surface) -> None:
        state = self.game.get_state()
        players = [
            {
                "id": pid,
                "name": state.players[pid].name,
                "position": self.shown_positions[pid],
                "color": PLAYER_COLORS[pid],
                "active": state.status == "RUNNING" and state.current_turn == pid and self.phase == "IDLE",
            }
            for pid in (PLAYER_1, PLAYER_2)
        ]
        self.hud.draw(surface, players, self.dice, self._status_text(), self._can_roll())
        if self.message:
            draw_text(surface, self.hud.font, self.message, config.COLOR_RED,
                      midbottom=(config.BASE_WIDTH // 2, config.HUD_TOP - 6))

    def _status_text(self) -> str:
        state = self.game.get_state()
        if self.phase == "ROLLING":
            return "ROLANDO..."
        if self.phase == "MOVING":
            return "ACELERANDO!"
        if state.status == "FINISHED":
            return "CORRIDA FINALIZADA"
        return f"VEZ DE {state.players[state.current_turn].name}"

    def _draw_finish_overlay(self, surface: pygame.Surface) -> None:
        state = self.game.get_state()
        shade = pygame.Surface((config.BASE_WIDTH, config.HUD_TOP), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        surface.blit(shade, (0, 0))
        center_x = config.BASE_WIDTH // 2
        winner = state.players[state.winner]
        draw_text(surface, self.font_title, "RACE FINISHED", config.COLOR_TEXT, center=(center_x, 150))
        draw_text(surface, self.font_title, f"{winner.name} WINS", PLAYER_COLORS[winner.id],
                  center=(center_x, 215))
        draw_text(surface, self.font, "[R] NOVA CORRIDA", config.COLOR_TEXT_DIM, center=(center_x, 280))
