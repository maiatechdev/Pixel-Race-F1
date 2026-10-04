import config


def world_x(position: float) -> float:
    return min(position, config.TRACK_LENGTH) * config.TRACK_UNIT_PX


class Camera:
    def __init__(self) -> None:
        self.x = 0.0

    @property
    def max_x(self) -> float:
        return world_x(config.TRACK_LENGTH) - (config.FINISH_REST_X - config.START_SCREEN_X)

    def follow(self, positions: list[float]) -> None:
        noses = [world_x(position) for position in positions]
        centered = (min(noses) + max(noses)) / 2 - (config.CAMERA_FOCUS_X - config.START_SCREEN_X)
        keep_leader_visible = max(noses) - (config.LEADER_MAX_SCREEN_X - config.START_SCREEN_X)
        self.x = min(max(centered, keep_leader_visible, 0.0), self.max_x)

    def to_screen(self, world: float) -> float:
        return config.START_SCREEN_X + world - self.x
