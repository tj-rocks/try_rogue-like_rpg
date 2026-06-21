import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["TEST_MODE"] = "1"
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from systems.combat_handler import calculate_damage, _is_back_attack
from constants import (
    CRITICAL_DAMAGE_MULTIPLIER,
    BACKSTAB_CRITICAL_DAMAGE_MULTIPLIER,
    BACKSTAB_CRIT_BONUS,
    CRITICAL_RATE_MAX,
    TILE_SIZE,
)


class DummyWeapon:
    def __init__(self, crit_rate=0.0):
        self.data = {"crit_rate": crit_rate}


class DummyEntity:
    def __init__(self, attack=0, defense=0, crit_rate=0.0, crit_bonus=0.0,
                 backstab_bonus=0.0, x=0, y=0, facing="down"):
        self.attack = attack
        self.total_attack = attack
        self.defense = defense
        self.total_defense = defense
        self.crit_rate = crit_rate
        self.crit_bonus = crit_bonus
        self.total_backstab_crit_bonus = backstab_bonus
        self.total_armor_penetration = 0.0
        self.weapon = DummyWeapon(crit_rate)
        self.x = x
        self.y = y
        self.facing = facing


def _force_random(crit=True, damage_roll=1.0):
    """クリティカル判定とダメージ乱数を固定する。"""
    random.random = lambda: 0.0 if crit else 0.9999
    random.uniform = lambda a, b: (b - a) * damage_roll


def _restore_random():
    random.random = _orig_random
    random.uniform = _orig_uniform


_orig_random = random.random
_orig_uniform = random.uniform


def test_normal_crit_damage():
    _force_random(crit=True, damage_roll=1.0)
    # crit_rate=1.0 で必ずクリティカルにする（正面判定）
    attacker = DummyEntity(attack=10, defense=0, crit_rate=1.0)
    target = DummyEntity(x=0, y=0, facing="left")
    attacker.x = -TILE_SIZE
    attacker.y = 0
    assert not _is_back_attack(attacker, target), "通常クリティカルテストが背後判定になっています"
    dmg, is_crit, _ = calculate_damage(attacker, target)
    _restore_random()
    expected = int(10 * CRITICAL_DAMAGE_MULTIPLIER)
    print(f"[通常クリティカル] ダメージ={dmg}, 期待値={expected}, 倍率={CRITICAL_DAMAGE_MULTIPLIER}")
    assert is_crit, "通常攻撃がクリティカルになっていません"
    assert dmg == expected, f"通常クリティカルダメージが期待値と異なります: {dmg} != {expected}"


def test_backstab_detection():
    target = DummyEntity(x=0, y=0, facing="left")
    attacker = DummyEntity(x=TILE_SIZE, y=0)  # target の右側
    assert _is_back_attack(attacker, target), "背後判定（left）が失敗"
    target.facing = "right"
    attacker.x = -TILE_SIZE
    assert _is_back_attack(attacker, target), "背後判定（right）が失敗"
    target.facing = "up"
    attacker.x = 0
    attacker.y = TILE_SIZE
    assert _is_back_attack(attacker, target), "背後判定（up）が失敗"
    target.facing = "down"
    attacker.y = -TILE_SIZE
    assert _is_back_attack(attacker, target), "背後判定（down）が失敗"
    print(f"[背後判定] 4方向すべて OK")


def test_backstab_crit_damage():
    _force_random(crit=True, damage_roll=1.0)
    attacker = DummyEntity(attack=10, defense=0, crit_rate=0.0)
    target = DummyEntity(x=0, y=0, facing="left")
    attacker.x = TILE_SIZE
    attacker.y = 0
    dmg, is_crit, _ = calculate_damage(attacker, target)
    _restore_random()
    expected = int(10 * BACKSTAB_CRITICAL_DAMAGE_MULTIPLIER)
    print(f"[バックスタブクリティカル] ダメージ={dmg}, 期待値={expected}, 倍率={BACKSTAB_CRITICAL_DAMAGE_MULTIPLIER}")
    assert is_crit, "バックスタブがクリティカルになっていません"
    assert dmg == expected, f"バックスタブダメージが期待値と異なります: {dmg} != {expected}"


def test_backstab_crit_rate_base():
    # 武器/会心率ボーナスなし、背後判定だけでクリティカル率 = BACKSTAB_CRIT_BONUS
    _force_random(crit=True)  # 判定値を 0 に固定 -> 必ずクリティカル
    attacker = DummyEntity(attack=10, defense=0, crit_rate=0.0, crit_bonus=0.0)
    target = DummyEntity(x=0, y=0, facing="left")
    attacker.x = TILE_SIZE
    _, is_crit, _ = calculate_damage(attacker, target)
    _restore_random()
    print(f"[バックスタブ会心率: 基本] クリティカル={is_crit}, 期待=下限{BACKSTAB_CRIT_BONUS}")
    assert is_crit, "BACKSTAB_CRIT_BONUS 分の会心率が適用されていません"


def test_backstab_crit_rate_with_bonus():
    # 装備ボーナス 0.1 + BACKSTAB_CRIT_BONUS = 0.25 + 0.1 = 0.35 (上限内)
    bonus = 0.1
    expected_rate = min(CRITICAL_RATE_MAX, BACKSTAB_CRIT_BONUS + bonus)
    # 判定値を期待レート未満に固定 -> クリティカルになる
    random.random = lambda: expected_rate - 0.001
    random.uniform = lambda a, b: 0.0  # ダメージは関係なし
    attacker = DummyEntity(attack=10, defense=0, crit_rate=0.0, crit_bonus=0.0, backstab_bonus=bonus)
    target = DummyEntity(x=0, y=0, facing="left")
    attacker.x = TILE_SIZE
    _, is_crit, _ = calculate_damage(attacker, target)
    _restore_random()
    print(f"[バックスタブ会心率: 装備ボーナス] bonus={bonus}, 合計レート={expected_rate}, クリティカル={is_crit}")
    assert is_crit, "装備 backstab_crit_bonus が加算されていません"


if __name__ == "__main__":
    test_normal_crit_damage()
    test_backstab_detection()
    test_backstab_crit_damage()
    test_backstab_crit_rate_base()
    test_backstab_crit_rate_with_bonus()
    print("\nすべての戦闘バランス検証テストに合格しました")
