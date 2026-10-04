import pygame

import config
from mock_game import MockGame
from screens.race import RaceScreen


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Distributed Racing")
    window = pygame.display.set_mode(
        (config.BASE_WIDTH * config.WINDOW_SCALE, config.BASE_HEIGHT * config.WINDOW_SCALE))
    canvas = pygame.Surface((config.BASE_WIDTH, config.BASE_HEIGHT))
    clock = pygame.time.Clock()

    screen = RaceScreen(MockGame())

    running = True
    while running:
        dt = clock.tick(config.FPS) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                if hasattr(event, "pos"):
                    event.pos = (event.pos[0] // config.WINDOW_SCALE, event.pos[1] // config.WINDOW_SCALE)
                screen.handle_event(event)

        screen.update(dt)

        screen.draw(canvas)
        pygame.transform.scale(canvas, window.get_size(), window)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
