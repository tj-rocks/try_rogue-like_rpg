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
    assert player.coin == 1234
    assert player.ending_clear_count == 1
    assert player.has_seen_ending is False
    assert player.dungeon_core_cleared is False
    assert player.defeated_once_only == ["other_once_enemy"]
    assert player.new_game_plus_pending is False


def test_enemy_attack_and_defense_scale_by_ending_clear_count():
    player = Player()
    player.ending_clear_count = 1

    enemy = Enemy(0, 0, "slime", player=player)
    data = ENEMY_DATA["slime"]

    assert enemy.attack == hardcore_round(data.get("attack", 0) * 1.3)
    assert enemy.defense == hardcore_round(data.get("defense", 0) * 1.3)


def test_enemy_multiplier_progression():
    player = Player()

    player.ending_clear_count = 0
    assert player.get_enemy_stat_multiplier() == 1.0

    player.ending_clear_count = 1
    assert player.get_enemy_stat_multiplier() == 1.3

    player.ending_clear_count = 2
    assert player.get_enemy_stat_multiplier() == 1.5

    player.ending_clear_count = 3
    assert player.get_enemy_stat_multiplier() == 1.7
