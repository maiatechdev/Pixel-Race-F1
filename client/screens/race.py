import queue

import pygame

import config
from assets import load_image, scale_to_height
from components.car import Car, load_wheel_frames, screen_x_for
from components.dice import Dice
from components.hud import Hud, draw_text
from components.parallax import ParallaxLayer
from game_state import PLAYER_1, PLAYER_2, GameState
from network import RacingClient

PLAYER_COLORS = {PLAYER_1: config.COLOR_RED, PLAYER_2: config.COLOR_BLUE}
CURB_HEIGHT = 8
CURB_SEGMENT = 24
CHECKER = 8

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
        self.connection_error = ""
        self.session_lost = ""

        wheel_frames = load_wheel_frames()
        self.cars = {
            PLAYER_1: Car("red", wheel_frames, config.LANE_RED_Y, self.shown_positions[PLAYER_1]),
            PLAYER_2: Car("blue", wheel_frames, config.LANE_BLUE_Y, self.shown_positions[PLAYER_2]),
        }

        self.backdrop = ParallaxLayer(
            scale_to_height(load_image("background/city_panorama.png"), config.BACKDROP_HEIGHT),
            y=0, speed_factor=config.PARALLAX_BACKDROP)
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
        self.font_title = pygame.font.Font(None, 64)
        self.font = pygame.font.Font(None, 28)

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
                and self.state.current_turn == self.my_id)

    def _request_roll(self) -> None:
        if not self._can_roll():
            return
        self.message = ""
        self.roll_pending = True
        self.dice.start_roll()
        self.client.request_roll()

    def update(self, dt: float):
        self._handle_network_events()
        self.dice.update(dt)

        if self.phase == IDLE:
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

        scroll = config.SCROLL_SPEED if self.phase == MOVING else 0.0
        self.backdrop.update(dt, scroll)
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
            elif kind == "connection_error":
                self._cancel_roll()
                self.connection_error = event[1]
            elif kind == "session_lost":
                self._cancel_roll()
                self.session_lost = event[1]

    def _apply_state(self, state: GameState) -> None:
        self.state = state
        for pid, player in state.players.items():
            self.names[pid] = player.name

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
        self.backdrop.draw(surface)
        self.asphalt.draw(surface)
        self._draw_track_markings(surface)
        self.cars[PLAYER_1].draw(surface)
        self.cars[PLAYER_2].draw(surface)
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

    def _draw_hud(self, surface: pygame.Surface) -> None:
        players = []
        for pid in (PLAYER_1, PLAYER_2):
            name = self.names.get(pid, "AGUARDANDO...")
            if pid == self.my_id:
                name += " (VOCÊ)"
            players.append({
                "id": pid,
                "name": name,
                "position": self.shown_positions[pid],
                "color": PLAYER_COLORS[pid],
                "active": (self.state.status == "RUNNING" and self.state.current_turn == pid
                           and self.phase == IDLE and not self._pending_move()),
            })
        self.hud.draw(surface, players, self.dice, self._status_text(), self._can_roll())

        warning = self.connection_error or self.message
        if warning:
            draw_text(surface, self.hud.font, warning, config.COLOR_RED,
                      midbottom=(config.BASE_WIDTH // 2, config.HUD_TOP - 6))

    def _status_text(self) -> str:
        if self.session_lost:
            return "DESCONECTADO"
        if self.connection_error:
            return "RECONECTANDO..."
        if self.phase == ROLLING or self.roll_pending:
            return "ROLANDO..."
        if self.phase == MOVING:
            return "ACELERANDO!"
        if self.state.status == "WAITING":
            return "AGUARDANDO"
        if self.state.status == "FINISHED":
            return "CORRIDA FINALIZADA"
        if self.state.current_turn == self.my_id:
            return "SUA VEZ"
        return "VEZ DO ADVERSÁRIO"

    def _draw_overlay(self, surface: pygame.Surface) -> None:
        if self.session_lost:
            self._draw_banner(surface, "DESCONECTADO", config.COLOR_RED, self.session_lost)
        elif self.state.status == "WAITING":
            self._draw_banner(surface, "AGUARDANDO ADVERSÁRIO", config.COLOR_TEXT,
                              f"Servidor {self.client.address}")
        elif self.state.status == "FINISHED" and self.phase == IDLE and not self._pending_move():
            winner = self.state.winner
            title = "VOCÊ VENCEU!" if winner == self.my_id else f"{self.names.get(winner, '')} VENCEU"
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
        draw_text(surface, self.font, "[ESC] SAIR", config.COLOR_TEXT_DIM, center=(center_x, 270))
