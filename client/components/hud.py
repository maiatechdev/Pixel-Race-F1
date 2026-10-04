import math

import pygame

import config
from assets import pixel_font, truncate
from components.dice import Dice

PANEL_MARGIN = 16
TEXT_GAP = 8
BAR_WIDTH = 232
BAR_HEIGHT = 8
CENTER_LEFT = 320
CENTER_RIGHT = 640
DICE_CENTER_X = 352
BUTTON_SIZE = (244, 32)
ALERT_PADDING = (14, 8)

BUTTON_READY = "ready"
BUTTON_WAITING = "waiting"
BUTTON_HIDDEN = "hidden"


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str,
              color: tuple[int, int, int], **anchor) -> pygame.Rect:
    image = font.render(text, False, color)
    rect = image.get_rect(**anchor)
    surface.blit(image, rect)
    return rect


def draw_alert(surface: pygame.Surface, message: str, hint: str,
               max_width: int = config.BASE_WIDTH - 80, **anchor) -> None:
    font = pixel_font(config.FONT_TEXT)
    small = pixel_font(config.FONT_SMALL)
    if font.size(message)[0] > max_width:
        font = small
    text_width = max(font.size(message)[0], small.size(hint)[0] if hint else 0)
    text_height = font.get_height() + (small.get_height() + 6 if hint else 0)
    box = pygame.Rect(0, 0, text_width + 2 * ALERT_PADDING[0], text_height + 2 * ALERT_PADDING[1])
    for name, value in anchor.items():
        setattr(box, name, value)
    pygame.draw.rect(surface, config.COLOR_HUD_BG, box)
    pygame.draw.rect(surface, config.COLOR_ALERT, box, 2)
    line = draw_text(surface, font, message, config.COLOR_ALERT,
                     midtop=(box.centerx, box.top + ALERT_PADDING[1]))
    if hint:
        draw_text(surface, small, hint, config.COLOR_TEXT, midtop=(box.centerx, line.bottom + 6))


class Hud:
    def __init__(self, helmets: dict[int, pygame.Surface]) -> None:
        self.helmets = helmets
        self.font = pixel_font(config.FONT_TEXT)
        self.font_small = pixel_font(config.FONT_SMALL)
        self.button_rect = pygame.Rect((0, 0), BUTTON_SIZE)
        self.button_rect.midright = (CENTER_RIGHT - 8, config.HUD_TOP + 60)

    def draw(self, surface: pygame.Surface, players: list[dict], dice: Dice,
             status: tuple[str, tuple[int, int, int]], button_state: str, clock: float) -> None:
        panel = pygame.Rect(0, config.HUD_TOP, config.BASE_WIDTH, config.BASE_HEIGHT - config.HUD_TOP)
        pygame.draw.rect(surface, config.COLOR_HUD_BG, panel)
        pygame.draw.line(surface, config.COLOR_HUD_BORDER, panel.topleft, panel.topright, 2)

        left, right = players
        self._draw_player(surface, left, align_right=False)
        self._draw_player(surface, right, align_right=True)

        status_text, status_color = status
        draw_text(surface, self.font, status_text, status_color,
                  midtop=((CENTER_LEFT + CENTER_RIGHT) // 2, config.HUD_TOP + 14))
        dice.draw(surface, (DICE_CENTER_X, config.HUD_TOP + 60))
        self._draw_button(surface, button_state, clock)

    def _draw_button(self, surface: pygame.Surface, state: str, clock: float) -> None:
        if state == BUTTON_HIDDEN:
            return
        if state == BUTTON_READY:
            bright = math.sin(clock * config.BUTTON_PULSE_HZ * 2 * math.pi) > 0
            fill = config.COLOR_YELLOW_BRIGHT if bright else config.COLOR_YELLOW
            pygame.draw.rect(surface, fill, self.button_rect)
            draw_text(surface, self.font, "ESPAÇO: JOGAR", config.COLOR_HUD_BG, center=self.button_rect.center)
        else:
            pygame.draw.rect(surface, config.COLOR_BUTTON_IDLE, self.button_rect, 2)
            draw_text(surface, self.font, "AGUARDE", config.COLOR_TEXT_DIM, center=self.button_rect.center)

    def _draw_player(self, surface: pygame.Surface, player: dict, align_right: bool) -> None:
        top = config.HUD_TOP + 14
        helmet = self.helmets[player["id"]]
        if align_right:
            helmet_rect = helmet.get_rect(topright=(config.BASE_WIDTH - PANEL_MARGIN, top - 4))
            text_x = helmet_rect.left - TEXT_GAP
            anchor = "topright"
        else:
            helmet_rect = helmet.get_rect(topleft=(PANEL_MARGIN, top - 4))
            text_x = helmet_rect.right + TEXT_GAP
            anchor = "topleft"
        surface.blit(helmet, helmet_rect)

        name = truncate(player["name"], config.HUD_NAME_MAX_CHARS)
        name_color = config.COLOR_YELLOW if player["active"] else config.COLOR_TEXT
        draw_text(surface, self.font, name, name_color, **{anchor: (text_x, top)})

        position = min(player["position"], config.TRACK_LENGTH)
        score = draw_text(surface, self.font, f"{position}/{config.TRACK_LENGTH}", config.COLOR_TEXT,
                          **{anchor: (text_x, top + 24)})
        if player["is_me"]:
            tag_x = score.right + TEXT_GAP if not align_right else score.left - TEXT_GAP
            tag_anchor = "midleft" if not align_right else "midright"
            draw_text(surface, self.font_small, "VOCÊ", config.COLOR_YELLOW,
                      **{tag_anchor: (tag_x, score.centery)})

        bar = pygame.Rect(0, 0, BAR_WIDTH, BAR_HEIGHT)
        setattr(bar, anchor, (text_x, top + 50))
        fill = bar.copy()
        fill.width = round(BAR_WIDTH * position / config.TRACK_LENGTH)
        pygame.draw.rect(surface, (50, 50, 70), bar)
        pygame.draw.rect(surface, player["color"], fill)
        pygame.draw.rect(surface, config.COLOR_HUD_BORDER, bar, 1)
