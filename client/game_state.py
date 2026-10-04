from dataclasses import dataclass

import racing_pb2

PLAYER_1 = 1
PLAYER_2 = 2


@dataclass(frozen=True)
class PlayerState:
    id: int
    name: str
    position: int


@dataclass(frozen=True)
class GameState:
    status: str
    players: dict[int, PlayerState]
    current_turn: int
    winner: int
    turn_number: int
    last_dice: int
    track_length: int


def from_proto(message: racing_pb2.GameState) -> GameState:
    return GameState(
        status=racing_pb2.GameStatus.Name(message.status),
        players={p.id: PlayerState(p.id, p.name, p.position) for p in message.players},
        current_turn=message.current_turn,
        winner=message.winner,
        turn_number=message.turn_number,
        last_dice=message.last_dice,
        track_length=message.track_length,
    )
