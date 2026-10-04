import argparse
from concurrent import futures

import grpc

import racing_pb2
import racing_pb2_grpc
from game import (Game, GameError, GameSnapshot, InvalidName, NotYourTurn, RaceNotRunning,
                  RoomFull, UnknownPlayer)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 50051
MAX_WORKERS = 10

STATUS_TO_PROTO = {
    "WAITING": racing_pb2.WAITING,
    "RUNNING": racing_pb2.RUNNING,
    "FINISHED": racing_pb2.FINISHED,
}

ERROR_TO_STATUS_CODE = {
    InvalidName: grpc.StatusCode.INVALID_ARGUMENT,
    RoomFull: grpc.StatusCode.RESOURCE_EXHAUSTED,
    UnknownPlayer: grpc.StatusCode.UNAUTHENTICATED,
    RaceNotRunning: grpc.StatusCode.FAILED_PRECONDITION,
    NotYourTurn: grpc.StatusCode.FAILED_PRECONDITION,
}


def to_proto(snapshot: GameSnapshot) -> racing_pb2.GameState:
    return racing_pb2.GameState(
        status=STATUS_TO_PROTO[snapshot.status],
        players=[racing_pb2.Player(id=p.id, name=p.name, position=p.position)
                 for p in snapshot.players],
        current_turn=snapshot.current_turn,
        winner=snapshot.winner,
        turn_number=snapshot.turn_number,
        last_dice=snapshot.last_dice,
        track_length=snapshot.track_length,
    )


def abort_with(context: grpc.ServicerContext, error: GameError) -> None:
    context.abort(ERROR_TO_STATUS_CODE[type(error)], str(error))


class RacingServicer(racing_pb2_grpc.RacingServiceServicer):
    def __init__(self, game: Game) -> None:
        self.game = game

    def JoinGame(self, request, context):
        try:
            player_id, token, snapshot = self.game.join(request.name)
        except GameError as error:
            abort_with(context, error)
        print(f"[join] {request.name} entrou como Player {player_id}")
        return racing_pb2.JoinGameResponse(player_id=player_id, token=token, state=to_proto(snapshot))

    def GetGameState(self, request, context):
        try:
            snapshot = self.game.get_state(request.token)
        except GameError as error:
            abort_with(context, error)
        return to_proto(snapshot)

    def RollDice(self, request, context):
        try:
            dice, snapshot = self.game.roll_dice(request.token)
        except GameError as error:
            abort_with(context, error)
        print(f"[roll] dado {dice} -> turno {snapshot.turn_number}, status {snapshot.status}")
        return racing_pb2.RollDiceResponse(dice=dice, state=to_proto(snapshot))

    def LeaveGame(self, request, context):
        try:
            self.game.leave(request.token)
        except GameError as error:
            abort_with(context, error)
        print("[leave] um jogador saiu da partida")
        return racing_pb2.LeaveGameResponse()


def create_server(game: Game, address: str) -> tuple[grpc.Server, int]:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=MAX_WORKERS))
    racing_pb2_grpc.add_RacingServiceServicer_to_server(RacingServicer(game), server)
    port = server.add_insecure_port(address)
    return server, port


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor do Distributed Racing")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    server, port = create_server(Game(), f"{args.host}:{args.port}")
    server.start()
    print(f"Servidor ouvindo em {args.host}:{port}")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(grace=1)


if __name__ == "__main__":
    main()
