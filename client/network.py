import queue
import threading

import grpc

import racing_pb2
import racing_pb2_grpc
from game_state import from_proto

POLL_INTERVAL_SECONDS = 0.25
CALL_TIMEOUT_SECONDS = 2.0
LEAVE_TIMEOUT_SECONDS = 1.0

ROLL = "roll"
STOP = "stop"

CONNECTION_CODES = {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED}


class RacingClient:
    def __init__(self, host: str, port: int, name: str) -> None:
        self.address = f"{host}:{port}"
        self.name = name
        self.events: queue.Queue = queue.Queue()
        self._commands: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._token = ""
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def request_roll(self) -> None:
        self._commands.put(ROLL)

    def close(self) -> None:
        self._stop.set()
        self._commands.put(STOP)
        if self._thread.is_alive():
            self._thread.join(timeout=CALL_TIMEOUT_SECONDS + LEAVE_TIMEOUT_SECONDS)

    def _run(self) -> None:
        with grpc.insecure_channel(self.address) as channel:
            stub = racing_pb2_grpc.RacingServiceStub(channel)
            if not self._join(stub):
                return
            while not self._stop.is_set():
                try:
                    command = self._commands.get(timeout=POLL_INTERVAL_SECONDS)
                except queue.Empty:
                    command = None
                if command == ROLL:
                    self._roll(stub)
                elif command is None:
                    self._poll(stub)
            self._leave(stub)

    def _join(self, stub) -> bool:
        try:
            response = stub.JoinGame(racing_pb2.JoinGameRequest(name=self.name),
                                     timeout=CALL_TIMEOUT_SECONDS)
        except grpc.RpcError as error:
            if error.code() in CONNECTION_CODES:
                message = f"Não foi possível conectar a {self.address}"
            else:
                message = self._describe(error)
            self.events.put(("join_failed", message))
            return False
        self._token = response.token
        self.events.put(("joined", response.player_id, from_proto(response.state)))
        return True

    def _roll(self, stub) -> None:
        try:
            response = stub.RollDice(racing_pb2.RollDiceRequest(token=self._token),
                                     timeout=CALL_TIMEOUT_SECONDS)
        except grpc.RpcError as error:
            self._report_error(error, "roll_rejected")
            return
        self.events.put(("rolled", response.dice, from_proto(response.state)))

    def _poll(self, stub) -> None:
        try:
            state = stub.GetGameState(racing_pb2.GetGameStateRequest(token=self._token),
                                      timeout=CALL_TIMEOUT_SECONDS)
        except grpc.RpcError as error:
            self._report_error(error, "connection_error")
            return
        self.events.put(("state", from_proto(state)))

    def _leave(self, stub) -> None:
        try:
            stub.LeaveGame(racing_pb2.LeaveGameRequest(token=self._token),
                           timeout=LEAVE_TIMEOUT_SECONDS)
        except grpc.RpcError:
            pass

    def _report_error(self, error: grpc.RpcError, kind: str) -> None:
        if error.code() == grpc.StatusCode.UNAUTHENTICATED:
            self.events.put(("session_lost", "O servidor encerrou sua sessão"))
            self._stop.set()
        elif error.code() in CONNECTION_CODES:
            self.events.put(("connection_error", self._describe(error)))
        else:
            self.events.put((kind, self._describe(error)))

    def _describe(self, error: grpc.RpcError) -> str:
        if error.code() == grpc.StatusCode.UNAVAILABLE:
            return f"Servidor indisponível em {self.address}"
        if error.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            return "O servidor não respondeu a tempo"
        return error.details() or str(error.code())
