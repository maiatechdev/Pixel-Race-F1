import random
from dataclasses import dataclass, field

TRACK_LENGTH = 30
PLAYER_1 = 1
PLAYER_2 = 2


@dataclass
class PlayerState:
    id: int
    name: str
    position: int


@dataclass
class GameState:
    status: str
    players: dict[int, PlayerState] = field(default_factory=dict)
    current_turn: int = PLAYER_1
    winner: int | None = None
    turn_number: int = 1
    last_dice: int | None = None


@dataclass
class RollResult:
    ok: bool
    dice: int | None = None
    error: str | None = None


def _initial_state() -> GameState:
    return GameState(
        status="RUNNING",
        players={
            PLAYER_1: PlayerState(PLAYER_1, "PLAYER 1", 12),
            PLAYER_2: PlayerState(PLAYER_2, "PLAYER 2", 9),
        },
        current_turn=PLAYER_1,
        last_dice=4,
    )


class MockGame:
    def __init__(self) -> None:
        self._state = _initial_state()

    def get_state(self) -> GameState:
        return self._state

    def roll_dice(self, player_id: int) -> RollResult:
        state = self._state
        if state.status != "RUNNING":
            return RollResult(ok=False, error="A corrida não está em andamento")
        if player_id != state.current_turn:
            return RollResult(ok=False, error="Não é o seu turno")

        dice = random.randint(1, 6)
        player = state.players[player_id]
        player.position += dice
        state.last_dice = dice

        if player.position >= TRACK_LENGTH:
            state.status = "FINISHED"
            state.winner = player_id
        else:
            state.current_turn = PLAYER_2 if player_id == PLAYER_1 else PLAYER_1
            state.turn_number += 1

        return RollResult(ok=True, dice=dice)

    def reset(self) -> None:
        self._state = _initial_state()
