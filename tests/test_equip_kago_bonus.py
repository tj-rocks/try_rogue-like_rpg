"""
test_equip_kago_bonus.py
「装備の加護」画面 (ui.py StatusDialog BONUS モード) で使われる
全ボーナス項目の合算値が正しく計算されているかを検証する。

テスト用装備 test_all_bonus_weapon / test_all_bonus_armor / test_all_bonus_shield を
実際のデータ(constants.py経由)からロードして EquipInstance.get_stat / get_enhance_bonus で
get_total_bonus() をシミュレートし、期待値と照合する。
"""
import os
import sys
import unittest

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制（本番セーブデータ保護）
os.environ["TEST_MODE"] = "1"

# Pygameをヘッドレス初期化
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player, EquipInstance
from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA


# ---------------------------------------------------------------------------
# ui.py の get_total_bonus() と同じロジックを再現するヘルパー
# ---------------------------------------------------------------------------
def get_total_bonus(equips, stat_key):
    """ui.py StatusDialog BONUS モードと同じ合算ロジック"""
    total = 0
    for inst in equips:
        base    = inst.get_stat(stat_key, 0)
        enhance = inst.get_enhance_bonus(stat_key) if hasattr(inst, "get_enhance_bonus") else 0
        total  += base + enhance
    return total


# ---------------------------------------------------------------------------
# テストクラス
# ---------------------------------------------------------------------------
class TestEquipKagoBonus(unittest.TestCase):
    """
    test_all_bonus_weapon / test_all_bonus_armor / test_all_bonus_shield を
    装備した状態で「装備の加護」全項目の合算値を検証する。

    テスト装備の定義は
      components/data/master/weapons.yml
      components/data/master/armors.yml
      components/data/master/shields.yml
    に記載されており、shop_buyable=false / floor_spawnable=false なので
    ゲームバランスには影響しない。
    """

    TEST_WEAPON_KEY = "test_all_bonus_weapon"
    TEST_ARMOR_KEY  = "test_all_bonus_armor"
    TEST_SHIELD_KEY = "test_all_bonus_shield"

    # -------------------------------------------------------------------
    # テスト装備のボーナス期待値（YAMLの値を直書き）
    # 変更した場合はこちらも合わせて更新すること
    # -------------------------------------------------------------------
    WEAPON_EXPECTED = {
        # common
        "attack_bonus":          15,
        "accuracy_bonus_close":  20,
        "accuracy_bonus_ranged": 10,
        "crit_rate":             0.15,
        "hp_bonus":              25,
        "defense_bonus":          5,
        "eva_bonus":             0.08,
        "block_chance_close":    0.0,
        "block_chance_ranged":   0.0,
        "magic_stave_bonus":     10,
        "regen_bonus":            1,
        # magic
        "magic_fire_damage":     0.20,
        "magic_fire_range":      1,
        "magic_heal_ratio":      0.10,
        "magic_knockback_damage":0.15,
        "magic_invincible_turns":1,
    }

    ARMOR_EXPECTED = {
        "attack_bonus":           5,
        "accuracy_bonus_close":  10,
        "accuracy_bonus_ranged":  5,
        "crit_rate":             0.10,
        "hp_bonus":              30,
        "defense_bonus":         15,
        "eva_bonus":             0.05,
        "block_chance_close":    0.0,
        "block_chance_ranged":   0.0,
        "magic_stave_bonus":      8,
        "regen_bonus":            2,
        "magic_fire_damage":     0.10,
        "magic_fire_range":      0,
        "magic_heal_ratio":      0.15,
        "magic_knockback_damage":0.10,
        "magic_invincible_turns":0,
    }

    SHIELD_EXPECTED = {
        "attack_bonus":           0,
        "accuracy_bonus_close":   5,
        "accuracy_bonus_ranged":  5,
        "crit_rate":             0.05,
        "hp_bonus":              10,
        "defense_bonus":          5,
        "eva_bonus":             0.03,
        "block_chance_close":    0.18,
        "block_chance_ranged":   0.18,
        "magic_stave_bonus":      5,
        "regen_bonus":            1,
        "magic_fire_damage":     0.05,
        "magic_fire_range":      1,
        "magic_heal_ratio":      0.05,
        "magic_knockback_damage":0.05,
        "magic_invincible_turns":1,
    }

    # ui.py で合算している全キー
    BONUS_KEYS = [
        "attack_bonus",
        "defense_bonus",
        "hp_bonus",
        "eva_bonus",
        "accuracy_bonus_close",
        "accuracy_bonus_ranged",
        "crit_rate",
        "block_chance_close",
        "block_chance_ranged",
        "magic_stave_bonus",
        "regen_bonus",
        "magic_fire_damage",
        "magic_fire_range",
        "magic_heal_ratio",
        "magic_knockback_damage",
        "magic_invincible_turns",
    ]

    def setUp(self):
        # テスト用装備がデータに存在することを確認
        self.assertIn(
            self.TEST_WEAPON_KEY, WEAPON_DATA,
            f"テスト装備 '{self.TEST_WEAPON_KEY}' が weapons.yml に存在しません"
        )
        self.assertIn(
            self.TEST_ARMOR_KEY, ARMOR_DATA,
            f"テスト装備 '{self.TEST_ARMOR_KEY}' が armors.yml に存在しません"
        )
        self.assertIn(
            self.TEST_SHIELD_KEY, SHIELD_DATA,
            f"テスト装備 '{self.TEST_SHIELD_KEY}' が shields.yml に存在しません"
        )

        self.weapon_inst = EquipInstance("weapon", self.TEST_WEAPON_KEY)
        self.armor_inst  = EquipInstance("armor",  self.TEST_ARMOR_KEY)
        self.shield_inst = EquipInstance("shield", self.TEST_SHIELD_KEY)
        self.equips = [self.weapon_inst, self.armor_inst, self.shield_inst]

    # -------------------------------------------------------------------
    # 1. 各装備単体でのフラット化確認
    # -------------------------------------------------------------------
    def test_weapon_stat_flatten(self):
        """テスト武器のボーナスがフラットキーで正しく参照できる"""
        for key, expected in self.WEAPON_EXPECTED.items():
            got = self.weapon_inst.get_stat(key, 0)
            self.assertAlmostEqual(
                got, expected, places=9,
                msg=f"weapon/{key}: expected {expected}, got {got}"
            )

    def test_armor_stat_flatten(self):
        """テスト鎧のボーナスがフラットキーで正しく参照できる"""
        for key, expected in self.ARMOR_EXPECTED.items():
            got = self.armor_inst.get_stat(key, 0)
            self.assertAlmostEqual(
                got, expected, places=9,
                msg=f"armor/{key}: expected {expected}, got {got}"
            )

    def test_shield_stat_flatten(self):
        """テスト盾のボーナスがフラットキーで正しく参照できる"""
        for key, expected in self.SHIELD_EXPECTED.items():
            got = self.shield_inst.get_stat(key, 0)
            self.assertAlmostEqual(
                got, expected, places=9,
                msg=f"shield/{key}: expected {expected}, got {got}"
            )

    # -------------------------------------------------------------------
    # 2. 全装備合算（ui.py BONUS モードと同じロジック）
    # -------------------------------------------------------------------
    def test_total_bonus_all_keys(self):
        """get_total_bonus() が ui.py と同じロジックで全項目を正しく合算する"""
        expected_totals = {
            key: (
                self.WEAPON_EXPECTED[key]
                + self.ARMOR_EXPECTED[key]
                + self.SHIELD_EXPECTED[key]
            )
            for key in self.BONUS_KEYS
        }

        for key in self.BONUS_KEYS:
            got      = get_total_bonus(self.equips, key)
            expected = expected_totals[key]
            self.assertAlmostEqual(
                got, expected, places=9,
                msg=f"total/{key}: expected {expected}, got {got}"
            )

    def test_total_attack_bonus(self):
        """攻撃力合計: weapon(15) + armor(5) + shield(0) = 20"""
        self.assertEqual(get_total_bonus(self.equips, "attack_bonus"), 20)

    def test_total_hp_bonus(self):
        """最大HP合計: weapon(25) + armor(30) + shield(10) = 65"""
        self.assertEqual(get_total_bonus(self.equips, "hp_bonus"), 65)

    def test_total_defense_bonus(self):
        """防御力合計: weapon(5) + armor(15) + shield(5) = 25"""
        self.assertEqual(get_total_bonus(self.equips, "defense_bonus"), 25)

    def test_total_accuracy_close(self):
        """近接命中合計: weapon(20) + armor(10) + shield(5) = 35"""
        self.assertEqual(get_total_bonus(self.equips, "accuracy_bonus_close"), 35)

    def test_total_accuracy_ranged(self):
        """遠隔命中合計: weapon(10) + armor(5) + shield(5) = 20"""
        self.assertEqual(get_total_bonus(self.equips, "accuracy_bonus_ranged"), 20)

    def test_total_crit_rate(self):
        """会心率合計: 0.15 + 0.10 + 0.05 = 0.30"""
        self.assertAlmostEqual(get_total_bonus(self.equips, "crit_rate"), 0.30, places=9)

    def test_total_eva_bonus(self):
        """回避率合計: 0.08 + 0.05 + 0.03 = 0.16"""
        self.assertAlmostEqual(get_total_bonus(self.equips, "eva_bonus"), 0.16, places=9)

    def test_total_block_chance_close(self):
        """近接ガード率合計: 0.0 + 0.0 + 0.18 = 0.18"""
        self.assertAlmostEqual(get_total_bonus(self.equips, "block_chance_close"), 0.18, places=9)

    def test_total_block_chance_ranged(self):
        """遠隔ガード率合計: 0.0 + 0.0 + 0.18 = 0.18"""
        self.assertAlmostEqual(get_total_bonus(self.equips, "block_chance_ranged"), 0.18, places=9)

    def test_total_stave_bonus(self):
        """杖強化合計: 10 + 8 + 5 = 23"""
        self.assertEqual(get_total_bonus(self.equips, "magic_stave_bonus"), 23)

    def test_total_regen_bonus(self):
        """自然回復合計: 1 + 2 + 1 = 4"""
        self.assertEqual(get_total_bonus(self.equips, "regen_bonus"), 4)

    def test_total_magic_fire_damage(self):
        """火炎ダメ合計: 0.20 + 0.10 + 0.05 = 0.35"""
        self.assertAlmostEqual(get_total_bonus(self.equips, "magic_fire_damage"), 0.35, places=9)

    def test_total_magic_fire_range(self):
        """火炎射程合計: 1 + 0 + 1 = 2"""
        self.assertEqual(get_total_bonus(self.equips, "magic_fire_range"), 2)

    def test_total_magic_heal_ratio(self):
        """回復効果合計: 0.10 + 0.15 + 0.05 = 0.30"""
        self.assertAlmostEqual(get_total_bonus(self.equips, "magic_heal_ratio"), 0.30, places=9)

    def test_total_magic_knockback(self):
        """吹飛ダメ合計: 0.15 + 0.10 + 0.05 = 0.30"""
        self.assertAlmostEqual(get_total_bonus(self.equips, "magic_knockback_damage"), 0.30, places=9)

    def test_total_magic_invincible_turns(self):
        """無敵ターン合計: 1 + 0 + 1 = 2"""
        self.assertEqual(get_total_bonus(self.equips, "magic_invincible_turns"), 2)

    # -------------------------------------------------------------------
    # 3. enhance=0 の場合は get_enhance_bonus が 0 を返すことを確認
    # -------------------------------------------------------------------
    def test_enhance_zero_gives_no_bonus(self):
        """強化値 enhance=0 のときは全項目で get_enhance_bonus が 0"""
        for inst in self.equips:
            for key in self.BONUS_KEYS:
                eb = inst.get_enhance_bonus(key)
                self.assertEqual(
                    eb, 0,
                    msg=f"{inst.key}/{key}: enhance=0 なのに get_enhance_bonus={eb}"
                )


if __name__ == "__main__":
    unittest.main()
