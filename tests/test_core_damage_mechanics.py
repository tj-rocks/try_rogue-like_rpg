from unittest.mock import patch

from components.sprites.enemy import Enemy
from components.sprites.player import Player
from systems.combat_handler import deal_damage


def test_core_normal_damage_is_capped_at_twenty():
    boss = Enemy(0, 0, "dungeon_core")
    player = Player()
    before_hp = boss.hp

    with patch("systems.combat_handler.calculate_damage", return_value=(99, False, False)):
        _, damage, _, _ = deal_damage(player, boss)

    assert damage == 20
    assert boss.hp == before_hp - 20


def test_core_percentage_attack_removes_thirty_percent_of_current_player_hp():
    boss = Enemy(0, 0, "dungeon_core")
    player = Player()
    player.hp = 101

    with patch("systems.combat_handler.calculate_damage", return_value=(4, False, False)), patch(
        "systems.combat_handler.random.random", return_value=0.0
    ):
        message, damage, _, _ = deal_damage(boss, player)

    assert damage == 31
    assert player.hp == 70
    assert player.percentage_damage_effect_timer == 20
    assert "割合ダメージ" in message


def test_core_percentage_attack_does_not_trigger_when_roll_fails():
    boss = Enemy(0, 0, "dungeon_core")
    player = Player()
    player.hp = 101

    with patch("systems.combat_handler.calculate_damage", return_value=(4, False, False)), patch(
        "systems.combat_handler.random.random", return_value=0.99
    ):
        _, damage, _, _ = deal_damage(boss, player)

    assert damage == 4
    assert player.hp == 97
