import pygame

import config
from components.dice import Dice

PANEL_MARGIN = 16
BAR_WIDTH = 220
BAR_HEIGHT = 8


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str,
              color: tuple[int, int, int], **anchor) -> pygame.Rect:
    image = font.render(text, False, color)
    rect = image.get_rect(**anchor)
    surface.blit(image, rect)
    return rect


class Hud:
    def __init__(self, helmets: dict[int, pygame.Surface]) -> None:
        self.helmets = helmets
        self.font_big = pygame.font.Font(None, 30)
        self.font = pygame.font.Font(None, 22)
        self.button_rect = pygame.Rect(0, 0, 210, 26)
        self.button_rect.midbottom = (config.BASE_WIDTH // 2, config.BASE_HEIGHT - 14)

    def draw(self, surface: pygame.Surface, players: list[dict], dice: Dice,
             status_text: str, button_enabled: bool) -> None:
        panel = pygame.Rect(0, config.HUD_TOP, config.BASE_WIDTH, config.BASE_HEIGHT - config.HUD_TOP)
        pygame.draw.rect(surface, config.COLOR_HUD_BG, panel)
        pygame.draw.line(surface, config.COLOR_HUD_BORDER, panel.topleft, panel.topright, 2)

        left, right = players
        self._draw_player(surface, left, align_right=False)
        self._draw_player(surface, right, align_right=True)

        center_x = config.BASE_WIDTH // 2
        dice.draw(surface, (center_x - 130, config.HUD_TOP + 45))
        draw_text(surface, self.font_big, status_text, config.COLOR_YELLOW,
                  midtop=(center_x, config.HUD_TOP + 16))

        color = config.COLOR_TEXT if button_enabled else config.COLOR_TEXT_DIM
        pygame.draw.rect(surface, color, self.button_rect, 2)
        draw_text(surface, self.font, "[ESPAÇO] JOGAR DADO", color, center=self.button_rect.center)

    def _draw_player(self, surface: pygame.Surface, player: dict, align_right: bool) -> None:
        top = config.HUD_TOP + 12
        helmet = self.helmets[player["id"]]
        if align_right:
            helmet_rect = helmet.get_rect(topright=(config.BASE_WIDTH - PANEL_MARGIN, top))
            text_x = helmet_rect.left - 8
            anchor = "topright"
        else:
            helmet_rect = helmet.get_rect(topleft=(PANEL_MARGIN, top))
            text_x = helmet_rect.right + 8
            anchor = "topleft"
        surface.blit(helmet, helmet_rect)

        name_color = config.COLOR_YELLOW if player["active"] else config.COLOR_TEXT
        draw_text(surface, self.font_big, player["name"], name_color, **{anchor: (text_x, top)})
        progress = f"P{player['id']}  {player['position']}/{config.TRACK_LENGTH}"
        draw_text(surface, self.font, progress, config.COLOR_TEXT, **{anchor: (text_x, top + 24)})

        bar = pygame.Rect(0, 0, BAR_WIDTH, BAR_HEIGHT)
        setattr(bar, anchor, (text_x, top + 46))
        fill_width = round(BAR_WIDTH * min(player["position"], config.TRACK_LENGTH) / config.TRACK_LENGTH)
        fill = bar.copy()
        fill.width = fill_width
        if align_right:
            fill.right = bar.right
        pygame.draw.rect(surface, (50, 50, 70), bar)
        pygame.draw.rect(surface, player["color"], fill)
        pygame.draw.rect(surface, config.COLOR_HUD_BORDER, bar, 1)
