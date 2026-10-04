import random
import threading
import time
import unittest

from game import (FINISHED, RUNNING, TRACK_LENGTH, WAITING, Game, InvalidName, NotYourTurn,
                  RaceNotRunning, RoomFull, UnknownPlayer)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class SlowRandom(random.Random):
    def randint(self, a, b):
        time.sleep(0.001)
        return super().randint(a, b)


def position_of(snapshot, player_id):
    return next(p.position for p in snapshot.players if p.id == player_id)


class JoinTest(unittest.TestCase):
    def test_first_player_waits(self):
        game = Game()
        player_id, token, state = game.join("Gabriel")
        self.assertEqual(player_id, 1)
        self.assertTrue(token)
        self.assertEqual(state.status, WAITING)

    def test_second_player_starts_race(self):
        game = Game()
        game.join("Gabriel")
        player_id, _, state = game.join("Lucas")
        self.assertEqual(player_id, 2)
        self.assertEqual(state.status, RUNNING)
        self.assertEqual(state.current_turn, 1)
        self.assertEqual([p.position for p in state.players], [0, 0])

    def test_third_player_is_rejected(self):
        game = Game()
        game.join("Gabriel")
        game.join("Lucas")
        with self.assertRaises(RoomFull):
            game.join("Ana")

    def test_empty_name_is_rejected(self):
        with self.assertRaises(InvalidName):
            Game().join("   ")

    def test_tokens_are_unique(self):
        game = Game()
        _, token_1, _ = game.join("Gabriel")
        _, token_2, _ = game.join("Lucas")
        self.assertNotEqual(token_1, token_2)


class RollDiceTest(unittest.TestCase):
    def setUp(self):
        self.game = Game(rng=random.Random(42))
        _, self.token_1, _ = self.game.join("Gabriel")
        _, self.token_2, _ = self.game.join("Lucas")

    def test_roll_moves_player_and_passes_turn(self):
        dice, state = self.game.roll_dice(self.token_1)
        self.assertIn(dice, range(1, 7))
        self.assertEqual(position_of(state, 1), dice)
        self.assertEqual(state.last_dice, dice)
        self.assertEqual(state.current_turn, 2)
        self.assertEqual(state.turn_number, 2)

    def test_roll_out_of_turn_is_rejected(self):
        with self.assertRaises(NotYourTurn):
            self.game.roll_dice(self.token_2)

    def test_unknown_token_is_rejected(self):
        with self.assertRaises(UnknownPlayer):
            self.game.roll_dice("token-falso")

    def test_roll_before_race_starts_is_rejected(self):
        game = Game()
        _, token, _ = game.join("Gabriel")
        with self.assertRaises(RaceNotRunning):
            game.roll_dice(token)

    def test_first_to_reach_track_length_wins(self):
        tokens = {1: self.token_1, 2: self.token_2}
        state = self.game.get_state(self.token_1)
        while state.status == RUNNING:
            _, state = self.game.roll_dice(tokens[state.current_turn])
        self.assertEqual(state.status, FINISHED)
        self.assertGreaterEqual(position_of(state, state.winner), TRACK_LENGTH)

    def test_no_roll_after_finish(self):
        tokens = {1: self.token_1, 2: self.token_2}
        state = self.game.get_state(self.token_1)
        while state.status == RUNNING:
            _, state = self.game.roll_dice(tokens[state.current_turn])
        for token in tokens.values():
            with self.assertRaises(RaceNotRunning):
                self.game.roll_dice(token)


class LeaveTest(unittest.TestCase):
    def test_leaving_during_race_gives_win_to_opponent(self):
        game = Game()
        _, token_1, _ = game.join("Gabriel")
        _, token_2, _ = game.join("Lucas")
        game.leave(token_1)
        state = game.get_state(token_2)
        self.assertEqual(state.status, FINISHED)
        self.assertEqual(state.winner, 2)

    def test_room_resets_when_everyone_leaves(self):
        game = Game()
        _, token_1, _ = game.join("Gabriel")
        _, token_2, _ = game.join("Lucas")
        game.leave(token_1)
        game.leave(token_2)
        player_id, _, state = game.join("Ana")
        self.assertEqual(player_id, 1)
        self.assertEqual(state.status, WAITING)

    def test_left_player_cannot_act(self):
        game = Game()
        _, token_1, _ = game.join("Gabriel")
        game.join("Lucas")
        game.leave(token_1)
        with self.assertRaises(UnknownPlayer):
            game.get_state(token_1)

    def test_inactive_player_is_removed_and_opponent_wins(self):
        clock = FakeClock()
        game = Game(clock=clock, timeout=5.0)
        _, token_1, _ = game.join("Gabriel")
        _, token_2, _ = game.join("Lucas")
        clock.now = 4.0
        game.get_state(token_2)
        clock.now = 6.0
        state = game.get_state(token_2)
        self.assertEqual(state.status, FINISHED)
        self.assertEqual(state.winner, 2)
        with self.assertRaises(UnknownPlayer):
            game.get_state(token_1)


class ConcurrencyTest(unittest.TestCase):
    THREADS = 50

    def run_simultaneously(self, action):
        barrier = threading.Barrier(self.THREADS)
        results = []
        results_lock = threading.Lock()

        def worker():
            barrier.wait()
            try:
                outcome = ("ok", action())
            except Exception as error:
                outcome = ("error", error)
            with results_lock:
                results.append(outcome)

        threads = [threading.Thread(target=worker) for _ in range(self.THREADS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return results

    def test_simultaneous_rolls_by_same_player_count_once(self):
        game = Game(rng=SlowRandom())
        _, token_1, _ = game.join("Gabriel")
        _, token_2, _ = game.join("Lucas")

        results = self.run_simultaneously(lambda: game.roll_dice(token_1))

        successes = [value for kind, value in results if kind == "ok"]
        failures = [value for kind, value in results if kind == "error"]
        self.assertEqual(len(successes), 1)
        self.assertTrue(all(isinstance(error, NotYourTurn) for error in failures))
        dice, _ = successes[0]
        state = game.get_state(token_2)
        self.assertEqual(position_of(state, 1), dice)
        self.assertEqual(state.current_turn, 2)
        self.assertEqual(state.turn_number, 2)

    def test_simultaneous_joins_never_exceed_two_players(self):
        game = Game()
        counter = iter(range(self.THREADS))
        counter_lock = threading.Lock()

        def join():
            with counter_lock:
                name = f"Jogador {next(counter)}"
            return game.join(name)

        results = self.run_simultaneously(join)

        successes = [value for kind, value in results if kind == "ok"]
        failures = [value for kind, value in results if kind == "error"]
        self.assertEqual(sorted(player_id for player_id, _, _ in successes), [1, 2])
        self.assertTrue(all(isinstance(error, RoomFull) for error in failures))


if __name__ == "__main__":
    unittest.main()
