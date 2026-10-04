import unittest

import grpc

import racing_pb2
import racing_pb2_grpc
from game import Game
from server import create_server


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.server, port = create_server(Game(), "127.0.0.1:0")
        self.server.start()
        self.channels = [grpc.insecure_channel(f"127.0.0.1:{port}") for _ in range(3)]
        self.client_1, self.client_2, self.client_3 = (
            racing_pb2_grpc.RacingServiceStub(channel) for channel in self.channels)

    def tearDown(self):
        for channel in self.channels:
            channel.close()
        self.server.stop(grace=None)

    def join_both(self):
        joined_1 = self.client_1.JoinGame(racing_pb2.JoinGameRequest(name="Gabriel"))
        joined_2 = self.client_2.JoinGame(racing_pb2.JoinGameRequest(name="Lucas"))
        return joined_1, joined_2

    def assert_status_code(self, code, call, request):
        with self.assertRaises(grpc.RpcError) as caught:
            call(request)
        self.assertEqual(caught.exception.code(), code)

    def test_two_clients_join_and_race_starts(self):
        joined_1, joined_2 = self.join_both()
        self.assertEqual(joined_1.player_id, 1)
        self.assertEqual(joined_2.player_id, 2)
        self.assertEqual(joined_1.state.status, racing_pb2.WAITING)
        self.assertEqual(joined_2.state.status, racing_pb2.RUNNING)

    def test_roll_is_seen_by_other_client(self):
        joined_1, joined_2 = self.join_both()
        rolled = self.client_1.RollDice(racing_pb2.RollDiceRequest(token=joined_1.token))
        seen_by_2 = self.client_2.GetGameState(racing_pb2.GetGameStateRequest(token=joined_2.token))
        self.assertEqual(seen_by_2, rolled.state)
        self.assertEqual(seen_by_2.players[0].position, rolled.dice)
        self.assertEqual(seen_by_2.current_turn, 2)
        self.assertEqual(seen_by_2.track_length, 30)

    def test_error_codes(self):
        joined_1, joined_2 = self.join_both()
        self.assert_status_code(grpc.StatusCode.FAILED_PRECONDITION, self.client_2.RollDice,
                                racing_pb2.RollDiceRequest(token=joined_2.token))
        self.assert_status_code(grpc.StatusCode.UNAUTHENTICATED, self.client_1.RollDice,
                                racing_pb2.RollDiceRequest(token="token-falso"))
        self.assert_status_code(grpc.StatusCode.RESOURCE_EXHAUSTED, self.client_3.JoinGame,
                                racing_pb2.JoinGameRequest(name="Ana"))

    def test_empty_name_is_invalid_argument(self):
        self.assert_status_code(grpc.StatusCode.INVALID_ARGUMENT, self.client_1.JoinGame,
                                racing_pb2.JoinGameRequest(name=""))

    def test_leave_gives_win_to_opponent(self):
        joined_1, joined_2 = self.join_both()
        self.client_1.LeaveGame(racing_pb2.LeaveGameRequest(token=joined_1.token))
        state = self.client_2.GetGameState(racing_pb2.GetGameStateRequest(token=joined_2.token))
        self.assertEqual(state.status, racing_pb2.FINISHED)
        self.assertEqual(state.winner, 2)


if __name__ == "__main__":
    unittest.main()
