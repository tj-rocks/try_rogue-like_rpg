from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from components.sprites.enemy import Enemy
from components.sprites.player import Player
from systems.game_state import game_state
from systems.magic_handler import execute_stave, FireEffect, KnockbackEffect


@pytest.fixture
def battle():
    saved_state = deepcopy(game_state)
    player = Player()
    player.x = player.target_x = 4 * 64
    player.y = player.target_y = 4 * 64
    player.hp = player.max_hp = 1000
    boss = Enemy(2 * 64, 4 * 64, "dungeon_core")
    boss.battle_locked = False
    dungeon = SimpleNamespace(
        tile_size=64, map_width=12, map_height=12,
        map_data=[[1] * 12 for _ in range(12)],
        enemies=[boss], magic_effects=[],
    )
    dialog = SimpleNamespace(text="", is_active=False)
    yield player, boss, dungeon, dialog
    game_state.clear()
    game_state.update(saved_state)


@pytest.mark.parametrize("effect,counter", [("fire", "fire"), ("barrier", "fire"), ("knockback", "knockback"), ("heal", None)])
def test_stave_selects_counter_and_uses_one_enemy_action(battle, effect, counter):
    player, boss, dungeon, dialog = battle
    stave = SimpleNamespace(key=f"{effect}_stave", name="テスト杖", charges=2)
    with patch(f"systems.magic_handler._effect_{effect}", return_value="効果発動"):
        execute_stave(player, stave, dungeon, dialog)
    assert stave.charges == 1
    assert boss.pending_magic_counter == counter
    with patch.object(boss, "_take_turn_dungeon_core") as normal, patch("components.sprites.enemy.deal_damage", return_value=("ダメージ", 10, False, False)) as damage:
        boss.take_turn(player, dungeon, [player, boss], dialog)
        if counter:
            normal.assert_not_called()
            assert damage.call_args.kwargs["is_magic"] is True
            assert damage.call_args.kwargs["damage_mult"] == (1.5 if counter == "fire" else 0.5)
            assert "魔法カウンター" in dialog.text
            assert any(isinstance(fx, FireEffect if counter == "fire" else KnockbackEffect) for fx in dungeon.magic_effects)
            if counter == "knockback":
                assert player.target_x == 6 * 64
        else:
            normal.assert_called_once()
            damage.assert_not_called()
        assert boss.pending_magic_counter is None
        damage.reset_mock()
        boss.take_turn(player, dungeon, [player, boss], dialog)
        damage.assert_not_called()


@pytest.mark.parametrize("state", ["dead", "locked", "empty"])
def test_no_counter_for_dead_locked_boss_or_empty_stave(battle, state):
    player, boss, dungeon, dialog = battle
    boss.is_dead = state == "dead"
    boss.battle_locked = state == "locked"
    stave = SimpleNamespace(key="fire_stave", name="炎の杖", charges=0 if state == "empty" else 1)
    with patch("systems.magic_handler._effect_fire", return_value="炎"):
        execute_stave(player, stave, dungeon, dialog)
    assert getattr(boss, "pending_magic_counter", None) is None


def test_lethal_stave_does_not_queue_counter(battle):
    player, boss, dungeon, dialog = battle
    stave = SimpleNamespace(key="fire_stave", name="炎の杖", charges=1)
    def kill(*args):
        boss.is_dead = True
        return "撃破"
    with patch("systems.magic_handler._effect_fire", side_effect=kill):
        execute_stave(player, stave, dungeon, dialog)
    assert getattr(boss, "pending_magic_counter", None) is None


def test_barrier_trap_does_not_prevent_magic_counter(battle):
    player, boss, dungeon, dialog = battle
    player.facing = "left"
    boss.x = boss.target_x = 3 * 64
    stave = SimpleNamespace(key="barrier_stave", name="障壁の杖", charges=1)
    execute_stave(player, stave, dungeon, dialog)
    assert any(e.type == "magic_barrier" for e in dungeon.enemies)
    with patch("components.sprites.enemy.deal_damage", return_value=("炎", 10, False, False)) as damage:
        boss.take_turn(player, dungeon, [player] + dungeon.enemies, dialog)
    damage.assert_called_once()


def test_stun_consumes_counter_without_delaying_it(battle):
    player, boss, dungeon, dialog = battle
    boss.pending_magic_counter = "fire"
    boss.stun_turns = 1
    with patch.object(boss, "_execute_magic_counter") as counter:
        boss.take_turn(player, dungeon, [player, boss], dialog)
    counter.assert_not_called()
    assert boss.pending_magic_counter is None


@pytest.mark.parametrize("invincible", [False, True])
def test_counter_uses_real_magic_damage_and_respects_invincibility(battle, invincible):
    player, boss, dungeon, dialog = battle
    player.invincible_turns = 1 if invincible else 0
    boss.pending_magic_counter = "fire"
    initial_hp = player.hp
    boss.take_turn(player, dungeon, [player, boss], dialog)
    if invincible:
        assert player.hp == initial_hp
    else:
        assert player.hp < initial_hp
