import random
import secrets
import threading
import time
from dataclasses import dataclass, field

TRACK_LENGTH = 30
MAX_PLAYERS = 2
DICE_SIDES = 6
PLAYER_TIMEOUT_SECONDS = 5.0
MAX_NAME_LENGTH = 24

WAITING = "WAITING"
RUNNING = "RUNNING"
FINISHED = "FINISHED"


class GameError(Exception):
    pass


class InvalidName(GameError):
    pass


class RoomFull(GameError):
    pass


class UnknownPlayer(GameError):
    pass


class RaceNotRunning(GameError):
    pass


class NotYourTurn(GameError):
    pass


@dataclass
class Player:
    id: int
    name: str
    token: str
    position: int = 0
    last_seen: float = 0.0


@dataclass(frozen=True)
class PlayerSnapshot:
    id: int
    name: str
    position: int


@dataclass(frozen=True)
class GameSnapshot:
    status: str
    players: tuple[PlayerSnapshot, ...]
    current_turn: int
    winner: int
    turn_number: int
    last_dice: int
    track_length: int = TRACK_LENGTH


@dataclass
class RaceState:
    status: str = WAITING
    players: dict[int, Player] = field(default_factory=dict)
    current_turn: int = 0
    winner: int = 0
    turn_number: int = 0
    last_dice: int = 0


class Game:
    def __init__(self, rng: random.Random | None = None, clock=time.monotonic,
                 timeout: float = PLAYER_TIMEOUT_SECONDS) -> None:
        self._lock = threading.Lock()
        self._rng = rng or random.Random()
        self._clock = clock
        self._timeout = timeout
        self._race = RaceState()

    def join(self, name: str) -> tuple[int, str, GameSnapshot]:
        name = name.strip()
        if not name:
            raise InvalidName("O nome não pode ser vazio")
        if len(name) > MAX_NAME_LENGTH:
            raise InvalidName(f"O nome pode ter no máximo {MAX_NAME_LENGTH} caracteres")
        if not name.isprintable():
            raise InvalidName("O nome tem caracteres inválidos")
        with self._lock:
            self._drop_inactive_players()
            race = self._race
            if race.status == RUNNING:
                raise RoomFull("Já existe uma corrida em andamento")
            if race.status == FINISHED:
                raise RoomFull("A corrida terminou; a sala libera quando os dois jogadores saírem")
            player_id = 1 if 1 not in race.players else 2
            token = secrets.token_hex(16)
            race.players[player_id] = Player(player_id, name, token, last_seen=self._clock())
            if len(race.players) == MAX_PLAYERS:
                race.status = RUNNING
                race.current_turn = 1
                race.turn_number = 1
            return player_id, token, self._snapshot()

    def get_state(self, token: str) -> GameSnapshot:
        with self._lock:
            self._drop_inactive_players()
            self._touch(self._find_player(token))
            return self._snapshot()

    def roll_dice(self, token: str) -> tuple[int, GameSnapshot]:
        with self._lock:
            self._drop_inactive_players()
            player = self._find_player(token)
            self._touch(player)
            race = self._race
            if race.status != RUNNING:
                raise RaceNotRunning("A corrida não está em andamento")
            if race.current_turn != player.id:
                raise NotYourTurn("Não é o seu turno")

            dice = self._rng.randint(1, DICE_SIDES)
            player.position += dice
            race.last_dice = dice
            if player.position >= TRACK_LENGTH:
                race.status = FINISHED
                race.winner = player.id
            else:
                race.current_turn = self._opponent_id(player.id)
                race.turn_number += 1
            return dice, self._snapshot()

    def leave(self, token: str) -> None:
        with self._lock:
            self._remove_player(self._find_player(token))

    def _find_player(self, token: str) -> Player:
        for player in self._race.players.values():
            if secrets.compare_digest(player.token, token):
                return player
        raise UnknownPlayer("Jogador não encontrado")

    def _touch(self, player: Player) -> None:
        player.last_seen = self._clock()

    def _drop_inactive_players(self) -> None:
        now = self._clock()
        for player in list(self._race.players.values()):
            if now - player.last_seen > self._timeout:
                self._remove_player(player)

    def _remove_player(self, player: Player) -> None:
        race = self._race
        del race.players[player.id]
        if race.status == RUNNING:
            race.status = FINISHED
            race.winner = self._opponent_id(player.id)
        if not race.players:
            self._race = RaceState()

    @staticmethod
    def _opponent_id(player_id: int) -> int:
        return 2 if player_id == 1 else 1

    def _snapshot(self) -> GameSnapshot:
        race = self._race
        players = tuple(
            PlayerSnapshot(p.id, p.name, p.position)
            for p in sorted(race.players.values(), key=lambda p: p.id)
        )
        return GameSnapshot(race.status, players, race.current_turn, race.winner,
                            race.turn_number, race.last_dice)
