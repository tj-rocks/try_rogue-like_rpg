import random
from collections import Counter
from types import SimpleNamespace
from unittest.mock import Mock, patch

from components.sprites.enemy import Enemy


def test_core_can_attack_after_turning_against_mobile_player():
    boss = Enemy(0, 0, "dungeon_core")
    boss.current_attack_mode = "line"
    boss.facing = "left"
    profile = Mock()
    profile.get_action_probability.side_effect = lambda action, **kwargs: 0.9 if action == "move" else 0.0
    player = SimpleNamespace(x=64, y=0, width=64, height=64, facing="left", tactical_profile=profile)
    with patch("components.sprites.enemy.random.random", return_value=0.85):
        boss._handle_attack(1, 0, player)
    assert boss.facing == "right"
    assert boss.is_attacking
    assert boss.target_for_attack is player
    assert Enemy(0, 0, "slime")._get_turn_attack_chance(player, "front", "1") == 0.05


def test_core_diagonal_prefers_attacking_to_waiting():
    boss = Enemy(0, 0, "dungeon_core")
    player = SimpleNamespace()
    rng = random.Random(42)
    with patch("components.sprites.enemy.random.choices", side_effect=rng.choices):
        actions = Counter(boss._choose_dungeon_core_diagonal_action(player)[0] for _ in range(1000))
    assert actions["diagonal"] > 750
    assert actions["wait"] < 100
    assert 100 < actions["step_front"] < 200


def test_core_advances_when_side_gap_prediction_is_not_selected():
    boss = Enemy(0, 0, "dungeon_core")
    player = SimpleNamespace()
    with patch("components.sprites.enemy.random.random", side_effect=[0.9, 0.85]), patch.object(boss, "_move_dungeon_core", return_value=True) as move, patch.object(boss, "_log_trace"), patch.object(boss, "_log_duel_trace"):
        assert boss._try_dungeon_core_side_gap_prediction(player, None, [], None, 2, 1, "side", "2")
    move.assert_called_once()


def test_core_prefers_direct_attacks_even_against_melee_habit():
    boss = Enemy(0, 0, "dungeon_core")
    profile = Mock()
    profile.get_preferred_action.return_value = "melee"
    profile.get_action_probability.side_effect = lambda action, **kwargs: 1.0 if action == "melee" else 0.0
    player = SimpleNamespace(tactical_profile=profile)
    with patch("components.sprites.enemy.get_relation_and_distance", return_value=("front", "1")), patch.object(boss, "_read_player_magic_habit", return_value=None):
        weights, _, _, _ = boss._get_dungeon_core_attack_weights(player, SimpleNamespace(tile_size=64))
    assert weights["counter"] <= 10
    assert weights["line"] > weights["counter"] * 5


def test_core_closes_distance_instead_of_waiting():
    boss = Enemy(0, 0, "dungeon_core")
    player = SimpleNamespace(x=640, y=0, width=64, height=64, facing="left")
    dungeon = SimpleNamespace(tile_size=64)
    with patch.object(boss, "_get_dungeon_core_attack_weights", return_value=({}, "far", "3plus", None)), patch.object(boss, "can_move_grid", return_value=True), patch.object(boss, "_log_trace"), patch.object(boss, "_log_duel_trace"), patch("components.sprites.enemy.random.randint", return_value=11):
        boss._take_turn_dungeon_core(player, dungeon, [player, boss])
    assert boss.is_moving
    assert boss.target_x == 64


def test_core_switches_from_prediction_after_five_prediction_misses():
    boss = Enemy(0, 0, "dungeon_core")
    boss.predicted_attack_miss_streak = 5
    assert boss._should_force_dungeon_core_non_prediction(None)
    assert boss.predicted_attack_miss_streak == 0
    assert not boss._should_force_dungeon_core_non_prediction(None)


def test_core_side_gap_repositions_after_five_prediction_misses():
    boss = Enemy(0, 0, "dungeon_core")
    boss.predicted_attack_miss_streak = 5
    player = SimpleNamespace()
    with patch.object(boss, "_move_dungeon_core", return_value=True) as move, patch.object(boss, "_log_trace"), patch.object(boss, "_log_duel_trace"):
        assert boss._try_dungeon_core_side_gap_prediction(player, None, [], None, 2, 1, "side", "2")
    move.assert_called_once_with(player, None, "side")
