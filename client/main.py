import argparse

import pygame

import config
from screens.connect import ConnectScreen

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 50051


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cliente do Distributed Racing")
    parser.add_argument("--name", default="")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pygame.init()
    pygame.display.set_caption("Distributed Racing")
    window = pygame.display.set_mode(
        (config.BASE_WIDTH * config.WINDOW_SCALE, config.BASE_HEIGHT * config.WINDOW_SCALE))
    canvas = pygame.Surface((config.BASE_WIDTH, config.BASE_HEIGHT))
    clock = pygame.time.Clock()

    screen = ConnectScreen(args.name, args.host, args.port)

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

        next_screen = screen.update(dt)
        if next_screen:
            screen = next_screen

        screen.draw(canvas)
        pygame.transform.scale(canvas, window.get_size(), window)
        pygame.display.flip()

    screen.close()
    pygame.quit()


if __name__ == "__main__":
    main()
