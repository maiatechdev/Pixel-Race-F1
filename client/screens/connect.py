import queue

import pygame

import config
from assets import load_image, pixel_font, scale_to_height
from components.hud import draw_alert, draw_text
from network import RacingClient
from screens.race import RaceScreen

FIELD_WIDTH = 432
FIELD_HEIGHT = 36
FIELD_GAP = 64
FIELDS_TOP = 200
FIELD_PADDING = 12
MAX_FIELD_LENGTH = 24
PANEL_WIDTH = 560
PANEL_TOP = 160
PANEL_HEIGHT = 330
TITLE_Y = 92
TITLE_SIZE = 40
TITLE_OUTLINE = (20, 20, 40)
CONNECTION_HINT = "Confira se o servidor está rodando e o endereço e a porta."


class TextField:
    def __init__(self, label: str, value: str, top: int) -> None:
        self.label = label
        self.value = value
        self.rect = pygame.Rect(0, 0, FIELD_WIDTH, FIELD_HEIGHT)
        self.rect.midtop = (config.BASE_WIDTH // 2, top)


class ConnectScreen:
    def __init__(self, name: str, host: str, port: int, error: str = "") -> None:
        self.fields = [
            TextField("NOME", name, FIELDS_TOP),
            TextField("SERVIDOR", host, FIELDS_TOP + FIELD_GAP),
            TextField("PORTA", str(port), FIELDS_TOP + 2 * FIELD_GAP),
        ]
        self.focus = 0 if not name else len(self.fields) - 1
        self.error = error
        self.client: RacingClient | None = None
        self.clock = 0.0
        self.background = scale_to_height(load_image("background/sky.png"), config.BASE_HEIGHT)
        self.font_title = pixel_font(TITLE_SIZE)
        self.font = pixel_font(config.FONT_TEXT)
        self.font_small = pixel_font(config.FONT_SMALL)
        pygame.key.start_text_input()

    @property
    def connecting(self) -> bool:
        return self.client is not None

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.connecting:
            return
        if event.type == pygame.TEXTINPUT:
            field = self.fields[self.focus]
            if len(field.value) < MAX_FIELD_LENGTH:
                field.value += event.text
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.fields[self.focus].value = self.fields[self.focus].value[:-1]
            elif event.key in (pygame.K_TAB, pygame.K_DOWN):
                self.focus = (self.focus + 1) % len(self.fields)
            elif event.key == pygame.K_UP:
                self.focus = (self.focus - 1) % len(self.fields)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._connect()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, field in enumerate(self.fields):
                if field.rect.collidepoint(event.pos):
                    self.focus = index

    def _connect(self) -> None:
        name, host, port_text = (field.value.strip() for field in self.fields)
        if not name:
            self.error = "Digite seu nome"
            return
        if not host:
            self.error = "Digite o endereço do servidor"
            return
        if not port_text.isdigit():
            self.error = "A porta deve ser um número"
            return
        self.error = ""
        self.client = RacingClient(host, int(port_text), name)
        self.client.start()

    def update(self, dt: float):
        self.clock += dt
        if not self.connecting:
            return None
        try:
            event = self.client.events.get_nowait()
        except queue.Empty:
            return None
        if event[0] == "joined":
            pygame.key.stop_text_input()
            _, player_id, state = event
            return RaceScreen(self.client, player_id, state)
        self.client.close()
        self.client = None
        self.error = event[1]
        return None

    def close(self) -> None:
        if self.client:
            self.client.close()

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.background, (0, 0))
        center_x = config.BASE_WIDTH // 2
        self._draw_title(surface, center_x)

        panel = pygame.Surface((PANEL_WIDTH, PANEL_HEIGHT), pygame.SRCALPHA)
        panel.fill((10, 10, 25, 225))
        surface.blit(panel, panel.get_rect(midtop=(center_x, PANEL_TOP)))

        for index, field in enumerate(self.fields):
            active = index == self.focus and not self.connecting
            draw_text(surface, self.font_small, field.label, config.COLOR_TEXT,
                      bottomleft=(field.rect.left, field.rect.top - 6))
            pygame.draw.rect(surface, config.COLOR_HUD_BG, field.rect)
            border = config.COLOR_YELLOW if active else config.COLOR_BUTTON_IDLE
            pygame.draw.rect(surface, border, field.rect, 2)
            cursor = "_" if active and int(self.clock * 2) % 2 == 0 else ""
            draw_text(surface, self.font, field.value + cursor, config.COLOR_TEXT,
                      midleft=(field.rect.left + FIELD_PADDING, field.rect.centery))

        hint_y = self.fields[-1].rect.bottom + 28
        if self.connecting:
            dots = "." * (int(self.clock * 3) % 4)
            draw_text(surface, self.font, f"CONECTANDO A {self.client.address}{dots}", config.COLOR_YELLOW,
                      midleft=(center_x - self.font.size(f"CONECTANDO A {self.client.address}...")[0] // 2, hint_y))
        else:
            draw_text(surface, self.font_small, "ENTER: CONECTAR   TAB: PRÓXIMO CAMPO   ESC: SAIR",
                      config.COLOR_TEXT, center=(center_x, hint_y))
        if self.error:
            hint = CONNECTION_HINT if "conectar" in self.error else ""
            draw_alert(surface, self.error, hint, max_width=PANEL_WIDTH - 40,
                       midbottom=(center_x, PANEL_TOP + PANEL_HEIGHT - 14))

    def _draw_title(self, surface: pygame.Surface, center_x: int) -> None:
        title = "DISTRIBUTED RACING"
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (4, 4)):
            draw_text(surface, self.font_title, title, TITLE_OUTLINE, center=(center_x + dx, TITLE_Y + dy))
        draw_text(surface, self.font_title, title, config.COLOR_TEXT, center=(center_x, TITLE_Y))
