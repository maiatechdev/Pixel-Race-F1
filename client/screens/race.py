import math
import queue

import pygame

import config
from assets import load_image, pixel_font, scale_to_height, truncate
from components.car import Car, load_wheel_frames, screen_x_for
from components.dice import Dice
from components.finish_celebration import FinishCelebration
from components.hud import BUTTON_HIDDEN, BUTTON_READY, BUTTON_WAITING, Hud, draw_alert, draw_text
from components.parallax import ParallaxLayer, PropLayer
from components.start_lights import StartLights
from game_state import PLAYER_1, PLAYER_2, GameState
from network import RacingClient

PLAYER_COLORS = {PLAYER_1: config.COLOR_RED, PLAYER_2: config.COLOR_BLUE}
CURB_HEIGHT = 8
CURB_SEGMENT = 24
CHECKER = 8
MARKER_HALF_WIDTH = 6
MARKER_HEIGHT = 6
MARKER_GAP = 6
OUTLINE = (20, 20, 32)
ALERT_TOP = 16

IDLE = "IDLE"
ROLLING = "ROLLING"
MOVING = "MOVING"


class RaceScreen:
    def __init__(self, client: RacingClient, player_id: int, state: GameState) -> None:
        self.client = client
        self.my_id = player_id
        self.state = state
        self.names = {pid: p.name for pid, p in state.players.items()}
        self.shown_positions = {PLAYER_1: 0, PLAYER_2: 0}
        self.shown_positions = {pid: self._server_position(pid) for pid in (PLAYER_1, PLAYER_2)}
        self.phase = IDLE
        self.moving_player = 0
        self.roll_pending = False
        self.message = ""
        self.message_timer = 0.0
        self.clock = 0.0
        self.connection_error = ""
        self.session_lost = ""

        wheel_frames = load_wheel_frames()
        self.cars = {
            PLAYER_1: Car("red", wheel_frames, config.LANE_RED_Y, self.shown_positions[PLAYER_1]),
            PLAYER_2: Car("blue", wheel_frames, config.LANE_BLUE_Y, self.shown_positions[PLAYER_2]),
        }

        self.backdrop = self._build_backdrop()
        self.start_lights = StartLights(load_image("circuit/starting_lights.png"))
        if state.status == "RUNNING":
            self.start_lights.start()
        track_height = config.TRACK_BOTTOM - config.TRACK_TOP
        self.asphalt = ParallaxLayer(
            scale_to_height(load_image("track/asphalt.png"), track_height),
            y=config.TRACK_TOP, speed_factor=config.PARALLAX_TRACK)

        helmets = {
            PLAYER_1: load_image("helmets/red.png"),
            PLAYER_2: load_image("helmets/blue.png"),
        }
        self.hud = Hud(helmets)
        self.dice = Dice(state.last_dice or None)
        self.font_title = pixel_font(config.FONT_TITLE)
        self.font_go = pixel_font(config.FONT_HERO)
        self.font = pixel_font(config.FONT_TEXT)
        self.font_small = pixel_font(config.FONT_SMALL)
        self.celebration = FinishCelebration()

    @staticmethod
    def _build_backdrop() -> list:
        sky = scale_to_height(load_image("background/sky.png"), config.SKY_HEIGHT)
        layers = [ParallaxLayer(sky, y=config.BACKDROP_HEIGHT - config.SKY_HEIGHT,
                                speed_factor=config.PARALLAX_SKY)]
        for path, bottom_y, speed_factor in config.BACKGROUND_LAYERS:
            image = load_image(path)
            layers.append(ParallaxLayer(image, y=bottom_y - image.get_height(), speed_factor=speed_factor))
        props = [(load_image(path), x) for path, x in config.TRACKSIDE_PROPS]
        layers.append(PropLayer(props, config.TRACKSIDE_BOTTOM, config.TRACKSIDE_PERIOD,
                                config.PARALLAX_TRACKSIDE))
        return layers

    def _server_position(self, player_id: int) -> int:
        player = self.state.players.get(player_id)
        return player.position if player else self.shown_positions.get(player_id, 0)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self._request_roll()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hud.button_rect.collidepoint(event.pos):
                self._request_roll()

    def _pending_move(self) -> int:
        for pid in (PLAYER_1, PLAYER_2):
            if self._server_position(pid) != self.shown_positions[pid]:
                return pid
        return 0

    def _can_roll(self) -> bool:
        return (self.phase == IDLE
                and not self.roll_pending
                and not self._pending_move()
                and not self.connection_error
                and not self.session_lost
                and self.state.status == "RUNNING"
                and self.state.current_turn == self.my_id
                and not self.start_lights.holding_race)

    def _request_roll(self) -> None:
        if not self._can_roll():
            return
        self.message = ""
        self.roll_pending = True
        self.dice.start_roll()
        self.client.request_roll()

    def update(self, dt: float):
        self.clock += dt
        if self.message:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""
        self._handle_network_events()
        self.dice.update(dt)
        self.start_lights.update(dt)
        self.celebration.update(dt)

        if self.phase == IDLE and not self.start_lights.holding_race:
            self._start_next_move()
        if self.phase == ROLLING and self.dice.done:
            self.cars[self.moving_player].move_to(self._server_position(self.moving_player))
            self.phase = MOVING

        for car in self.cars.values():
            car.update(dt)

        if self.phase == MOVING and not self.cars[self.moving_player].is_moving:
            self.shown_positions[self.moving_player] = self._server_position(self.moving_player)
            self.moving_player = 0
            self.phase = IDLE

        if self._winner_crossed_line() and not self.celebration.started:
            finish_x = round(screen_x_for(config.TRACK_LENGTH))
            self.celebration.start(finish_x + config.FLAG_POLE_OFFSET_X, config.TRACK_TOP + 4)

        scroll = config.SCROLL_SPEED if self.phase == MOVING else 0.0
        for layer in self.backdrop:
            layer.update(dt, scroll)
        self.asphalt.update(dt, scroll)
        return None

    def _handle_network_events(self) -> None:
        while True:
            try:
                event = self.client.events.get_nowait()
            except queue.Empty:
                return
            kind = event[0]
            if kind == "state":
                self._apply_state(event[1])
                self.connection_error = ""
            elif kind == "rolled":
                self.roll_pending = False
                self._apply_state(event[2])
            elif kind == "roll_rejected":
                self._cancel_roll()
                self.message = event[1]
                self.message_timer = config.MESSAGE_SECONDS
            elif kind == "connection_error":
                self._cancel_roll()
                self.connection_error = event[1]
            elif kind == "session_lost":
                self._cancel_roll()
                self.session_lost = event[1]

    def _apply_state(self, state: GameState) -> None:
        self.state = state
        if state.status == "RUNNING":
            self.start_lights.start()
        for pid, player in state.players.items():
            self.names[pid] = player.name

    def _race_settled(self) -> bool:
        return self.state.status == "FINISHED" and self.phase == IDLE and not self._pending_move()

    def _winner_crossed_line(self) -> bool:
        return (self._race_settled()
                and self._server_position(self.state.winner) >= self.state.track_length)

    def _cancel_roll(self) -> None:
        if self.roll_pending:
            self.roll_pending = False
            self.dice.cancel()

    def _start_next_move(self) -> None:
        pid = self._pending_move()
        if not pid:
            return
        dice_value = self._server_position(pid) - self.shown_positions[pid]
        if not self.dice.rolling:
            self.dice.start_roll()
        self.dice.set_result(dice_value)
        self.moving_player = pid
        self.phase = ROLLING

    def close(self) -> None:
        self.client.close()

    def draw(self, surface: pygame.Surface) -> None:
        for layer in self.backdrop:
            layer.draw(surface)
        self.asphalt.draw(surface)
        self._draw_track_markings(surface)
        self._draw_start_gantry(surface)
        self.cars[PLAYER_1].draw(surface)
        self.cars[PLAYER_2].draw(surface)
        self._draw_you_marker(surface)
        self.celebration.draw(surface)
        self._draw_hud(surface)
        self._draw_overlay(surface)

    def _draw_track_markings(self, surface: pygame.Surface) -> None:
        offset = int(self.asphalt.offset)
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

    def _draw_start_gantry(self, surface: pygame.Surface) -> None:
        start_x = round(screen_x_for(0))
        rect = self.start_lights.lit_image.get_rect(left=start_x - config.GANTRY_POST_OFFSET_X,
                                                    bottom=config.TRACK_TOP + config.GANTRY_OVERHANG)
        self.start_lights.draw(surface, rect.topleft)

    def _draw_you_marker(self, surface: pygame.Surface) -> None:
        body = self.cars[self.my_id].body_rect()
        bob = round(math.sin(self.clock * 4))
        tip = (body.centerx, body.top - MARKER_GAP + bob)
        triangle = [tip, (tip[0] - MARKER_HALF_WIDTH, tip[1] - MARKER_HEIGHT),
                    (tip[0] + MARKER_HALF_WIDTH, tip[1] - MARKER_HEIGHT)]
        pygame.draw.polygon(surface, OUTLINE, [(x, y + 1) for x, y in triangle])
        pygame.draw.polygon(surface, config.COLOR_YELLOW, triangle)
        label_x, label_y = tip[0], tip[1] - MARKER_HEIGHT - 3
        draw_text(surface, self.font_small, "VOCÊ", OUTLINE, midbottom=(label_x + 1, label_y + 1))
        draw_text(surface, self.font_small, "VOCÊ", config.COLOR_YELLOW, midbottom=(label_x, label_y))

    def _draw_hud(self, surface: pygame.Surface) -> None:
        players = []
        for pid in (PLAYER_1, PLAYER_2):
            players.append({
                "id": pid,
                "name": self.names.get(pid, "AGUARDANDO"),
                "position": self.shown_positions[pid],
                "color": PLAYER_COLORS[pid],
                "is_me": pid == self.my_id,
                "active": (self.state.status == "RUNNING" and self.state.current_turn == pid
                           and self.phase == IDLE and not self._pending_move()
                           and not self.start_lights.holding_race
                           and not self.connection_error and not self.session_lost),
            })
        self.hud.draw(surface, players, self.dice, self._status(), self._button_state(), self.clock)

        alert_top = (config.BASE_WIDTH // 2, ALERT_TOP)
        if self.connection_error and not self.session_lost:
            draw_alert(surface, self.connection_error,
                       "Tentando reconectar. Confira se o servidor continua rodando.", midtop=alert_top)
        elif self.message:
            draw_alert(surface, self.message, "", midtop=alert_top)

    def _button_state(self) -> str:
        if self.session_lost or self.state.status == "FINISHED":
            return BUTTON_HIDDEN
        return BUTTON_READY if self._can_roll() else BUTTON_WAITING

    def _status(self) -> tuple[str, tuple[int, int, int]]:
        if self.session_lost:
            return "DESCONECTADO", config.COLOR_ALERT
        if self.connection_error:
            return "RECONECTANDO...", config.COLOR_ALERT
        if self.phase == ROLLING or self.roll_pending:
            return "ROLANDO...", config.COLOR_TEXT
        if self.phase == MOVING:
            return "ACELERANDO!", config.COLOR_TEXT
        if self.start_lights.holding_race:
            return "PREPARAR...", config.COLOR_TEXT
        if self.state.status == "WAITING":
            return "AGUARDANDO", config.COLOR_TEXT
        if self.state.status == "FINISHED":
            return "FIM DE CORRIDA", config.COLOR_TEXT
        if self.state.current_turn == self.my_id:
            return "SUA VEZ!", config.COLOR_YELLOW
        opponent = truncate(self.names.get(self.state.current_turn, ""), 10)
        return f"VEZ DE {opponent}", config.COLOR_TEXT

    def _draw_overlay(self, surface: pygame.Surface) -> None:
        if self.session_lost:
            self._draw_banner(surface, "DESCONECTADO", config.COLOR_RED, self.session_lost)
        elif self.start_lights.showing_go:
            draw_text(surface, self.font_go, "GO!", (20, 20, 20), center=(config.BASE_WIDTH // 2 + 4, 184))
            draw_text(surface, self.font_go, "GO!", config.COLOR_GO, center=(config.BASE_WIDTH // 2, 180))
        elif self.state.status == "WAITING":
            self._draw_banner(surface, "AGUARDANDO ADVERSÁRIO", config.COLOR_TEXT,
                              f"Servidor {self.client.address}")
        elif self._race_settled() and (self.celebration.done or not self._winner_crossed_line()):
            winner = self.state.winner
            winner_name = truncate(self.names.get(winner, ""), config.HUD_NAME_MAX_CHARS)
            title = "VOCÊ VENCEU!" if winner == self.my_id else f"{winner_name} VENCEU"
            subtitle = ""
            if self._server_position(winner) < self.state.track_length:
                subtitle = "O adversário saiu da corrida"
            self._draw_banner(surface, title, PLAYER_COLORS.get(winner, config.COLOR_TEXT), subtitle)

    def _draw_banner(self, surface: pygame.Surface, title: str, color, subtitle: str) -> None:
        shade = pygame.Surface((config.BASE_WIDTH, config.HUD_TOP), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        surface.blit(shade, (0, 0))
        center_x = config.BASE_WIDTH // 2
        draw_text(surface, self.font_title, title, color, center=(center_x, 160))
        if subtitle:
            draw_text(surface, self.font, subtitle, config.COLOR_TEXT, center=(center_x, 220))
        draw_text(surface, self.font, "ESC: SAIR", config.COLOR_TEXT_DIM, center=(center_x, 270))
