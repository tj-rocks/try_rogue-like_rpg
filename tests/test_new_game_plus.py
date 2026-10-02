import os
import sys

os.environ["TEST_MODE"] = "1"
os.environ["SDL_VIDEODRIVER"] = "dummy"

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.enemy import Enemy
from components.sprites.player import Player
from constants import ENEMY_DATA
from systems.math_utils import hardcore_round


def test_new_game_plus_pending_resets_rank_and_gp_only():
    player = Player()
    player.guild_rank = "SS"
    player.guild_point = 9999
    player.max_reached_floor = 99
    player.coin = 1234
    player.ending_clear_count = 1
    player.new_game_plus_pending = True
    player.has_seen_ending = True
    player.dungeon_core_cleared = True
    player.defeated_once_only = ["undead_father", "dungeon_core", "other_once_enemy"]

    applied = player.apply_new_game_plus_start()

    assert applied is True
    assert player.guild_rank == "-"
    assert player.guild_point == 0
    assert player.max_reached_floor == 99
    assert player.coin == 1234
    assert player.ending_clear_count == 1
    assert player.has_seen_ending is False
    assert player.dungeon_core_cleared is False
    assert player.defeated_once_only == ["other_once_enemy"]
    assert player.new_game_plus_pending is False


def test_enemy_hp_attack_and_defense_scale_by_difficulty_bonus():
    player = Player()
    player.difficulty_bonus = 0.20

    enemy = Enemy(0, 0, "slime", player=player)
    data = ENEMY_DATA["slime"]

    assert enemy.max_hp == hardcore_round(data.get("hp", 0) * 1.2, is_hp=True)
    assert enemy.attack == hardcore_round(data.get("attack", 0) * 1.2)
    assert enemy.defense == hardcore_round(data.get("defense", 0) * 1.2)


def test_enemy_multiplier_uses_saved_difficulty_bonus():
    player = Player()
    player.difficulty_bonus = 0.0
    assert player.get_enemy_stat_multiplier() == 1.0

    player.difficulty_bonus = 0.20
    assert player.get_enemy_stat_multiplier() == 1.2

    player.difficulty_bonus = 0.40
    assert player.get_enemy_stat_multiplier() == 1.4


def test_core_ending_save_resets_max_reached_floor():
    from types import SimpleNamespace
    from systems.scene_handler import save_core_clear_before_ending

    player = SimpleNamespace(
        has_seen_ending=False,
        dungeon_core_cleared=False,
        ending_clear_count=0,
        difficulty_bonus=0.0,
        max_reached_floor=99,
        new_game_plus_pending=False,
        save_to_file=lambda **kwargs: None,
    )
    game_state = {}

    assert save_core_clear_before_ending(player, game_state)
    assert player.max_reached_floor == 0
    assert player.difficulty_bonus == 0.20
    assert player.new_game_plus_pending is True
