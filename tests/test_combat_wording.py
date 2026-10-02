from contextlib import ExitStack
from unittest.mock import PropertyMock, patch

import pytest

from components.sprites.enemy import Enemy
from components.sprites.player import Player
from systems.combat_handler import deal_damage


@pytest.mark.parametrize("effect,expected", [
    ("block", "盾で 攻撃を ブロックした"),
    ("poison", "毒を受けてしまった"),
    ("darkness", "暗闇に包まれた"),
    ("stun", "スタンした"),
    ("lifesteal", "10回復した"),
    ("counter", "反撃！"),
])
def test_player_effect_messages_omit_self_name(effect, expected):
    player = Player()
    enemy = Enemy(0, 0, "slime")
    player.max_hp = enemy.max_hp = 1000
    player.hp = enemy.hp = 500
    attacker, target = enemy, player
    with ExitStack() as stack:
        stack.enter_context(patch("systems.combat_handler.calculate_damage", return_value=(0 if effect == "block" else 50, True, False)))
        stack.enter_context(patch("systems.combat_handler.random.random", return_value=0.0))
        if effect in ("poison", "darkness"):
            enemy.status_to_inflict = effect
            enemy.status_chance = 100
        elif effect == "stun":
            player.stun_turns = 0
            enemy.total_stun = 2
            enemy.total_stun_proc_chance = 1.0
            enemy.total_stun_duration = 1
        elif effect == "lifesteal":
            attacker, target = player, enemy
            for name, value in [("total_lifesteal", 2), ("total_lifesteal_chance", 1.0), ("total_lifesteal_ratio", 0.2)]:
                stack.enter_context(patch.object(Player, name, new_callable=PropertyMock, return_value=value))
        elif effect == "counter":
            for name, value in [("total_counter", 2), ("total_counter_proc_chance", 1.0), ("total_counter_damage_ratio", 0.5)]:
                stack.enter_context(patch.object(Player, name, new_callable=PropertyMock, return_value=value))
        message, _, _, _ = deal_damage(attacker, target)
    assert expected in message
    assert "自分" not in message


def test_enemy_status_message_keeps_enemy_name():
    player = Player()
    enemy = Enemy(0, 0, "slime")
    enemy.hp = enemy.max_hp = 1000
    enemy.condition = "normal"
    player.status_to_inflict = "poison"
    player.status_chance = 100
    with patch("systems.combat_handler.calculate_damage", return_value=(10, False, False)):
        message, _, _, _ = deal_damage(player, enemy)
    assert f"{enemy.name}は毒を受けてしまった" in message
