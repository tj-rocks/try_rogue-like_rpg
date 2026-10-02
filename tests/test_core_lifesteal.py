from unittest.mock import patch

import pytest

from components.sprites.enemy import Enemy
from components.sprites.player import Player
from systems.combat_handler import deal_damage


@pytest.mark.parametrize("damage,critical,miss,hp,healed", [
    (50, True, False, 100, 10),
    (19, True, False, 100, 3),
    (50, False, False, 100, 0),
    (0, False, True, 100, 0),
    (0, True, False, 100, 0),
    (50, True, False, "almost_full", 1),
    (50, True, False, "full", 0),
])
def test_core_lifesteal(damage, critical, miss, hp, healed):
    boss = Enemy(0, 0, "dungeon_core")
    boss.activate_battle_equipment()
    boss.current_hp_damage_chance = 0.0  # ライフスティール単体を検証するため割合攻撃を無効化
    if hp == "almost_full":
        hp = boss.max_hp - 1
    elif hp == "full":
        hp = boss.max_hp
    boss.hp = hp
    player = Player()
    player.hp = player.max_hp = 1000
    with patch("systems.combat_handler.calculate_damage", return_value=(damage, critical, miss)):
        message, _, _, _ = deal_damage(boss, player)
    assert boss.hp == hp + healed
    if healed:
        assert "回復した" in message


def test_other_enemies_do_not_gain_lifesteal():
    enemy = Enemy(0, 0, "slime")
    enemy.hp = 1
    player = Player()
    player.hp = player.max_hp = 1000
    with patch("systems.combat_handler.calculate_damage", return_value=(50, True, False)):
        deal_damage(enemy, player)
    assert enemy.hp == 1
