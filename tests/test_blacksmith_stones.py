import os
import sys
import unittest
import pygame

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["TEST_MODE"] = "1"
os.environ["SDL_VIDEODRIVER"] = "dummy"

pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player, EquipInstance, ORE_STAT_CATEGORIES
from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA

class TestBlacksmithStones(unittest.TestCase):
    def setUp(self):
        # Create a mock/custom EquipInstance for testing
        self.weapon = EquipInstance("weapon", "iron_sword")
        # Ensure it has basic stats for test: attack_bonus, accuracy_bonus_close, crit_rate
        # We also mock get_stat to have custom control over test stats
        self.weapon.get_stat = lambda k, d=0: {
            "attack_bonus": 10,
            "crit_rate": 0.05,
            "block_chance_close": 0.05,
            "name": "テストの剣"
        }.get(k, d)

        # attack_bonus, crit_rate, block_chance_close should be upgradeable
        stats = self.weapon.get_base_upgradeable_stats()
        self.assertIn("attack_bonus", stats)
        self.assertIn("crit_rate", stats)
        self.assertIn("block_chance_close", stats)
        # defense_bonus is 0, so should not be in upgradeable stats
        self.assertNotIn("defense_bonus", stats)

    def test_ore_compatibility(self):
        # red_stone is compatible because of attack_bonus and crit_rate
        self.assertTrue(self.weapon.is_ore_compatible("red_stone"))
        # green_stone is compatible because of block_chance_close
        self.assertTrue(self.weapon.is_ore_compatible("green_stone"))
        # blue_stone is not compatible because there are no defense stats
        self.assertFalse(self.weapon.is_ore_compatible("blue_stone"))
        # purple_stone is not compatible because there are no magic stats
        self.assertFalse(self.weapon.is_ore_compatible("purple_stone"))
        # General ores are no longer compatible
        self.assertFalse(self.weapon.is_ore_compatible("copper_ore"))

    def test_apply_upgrade_colored_stone(self):
        # Apply upgrade to specific stat
        self.weapon.apply_upgrade("attack_bonus", 1)
        
        # Only attack_bonus should be upgraded to 1
        self.assertEqual(self.weapon.stats.get("attack_bonus"), 1)
        # Other stats (crit_rate, block_chance_close) should remain at 0 (initialized to 0 before upgrade, not incremented)
        self.assertEqual(self.weapon.stats.get("crit_rate"), 0)
        self.assertEqual(self.weapon.stats.get("block_chance_close"), 0)
        # Overall enhance should be 1
        self.assertEqual(self.weapon.enhance, 1)

    def test_growth_decay_curve(self):
        # 新方式: per-stat の強化回数(self.stats)に基づく減衰カーブ。
        # 1-10回の区間は times_limit に依存せず安定（整数系は growth_room=10 -> +0.5/回）。
        self.weapon.stats = {"attack_bonus": 1}
        self.assertAlmostEqual(self.weapon.get_enhance_bonus("attack_bonus"), 0.5)

        self.weapon.stats = {"attack_bonus": 10}
        self.assertAlmostEqual(self.weapon.get_enhance_bonus("attack_bonus"), 5.0)

        # 強化回数が増えるほどボーナスは単調増加する
        self.weapon.stats = {"attack_bonus": 20}
        b20 = self.weapon.get_enhance_bonus("attack_bonus")
        self.weapon.stats = {"attack_bonus": 50}
        b50 = self.weapon.get_enhance_bonus("attack_bonus")
        self.assertGreater(b20, 5.0)
        self.assertGreater(b50, b20)

        # enhance 単体（stats にキーがない）ではボーナスは出ない（旧セーブ互換は廃止）
        self.weapon.stats = {}
        self.weapon.enhance = 30
        self.assertEqual(self.weapon.get_enhance_bonus("attack_bonus"), 0)

    def test_no_enhance_fallback(self):
        # 新方式: stats が空なら enhance を持っていてもボーナスは0（旧セーブ互換なし）
        self.weapon.enhance = 5
        self.weapon.stats = {}
        self.assertEqual(self.weapon.get_enhance_bonus("attack_bonus"), 0)
        self.assertEqual(self.weapon.get_enhance_bonus("block_chance_close"), 0)

        # apply_upgrade 時は未初期化の stat を現 enhance 値(5)で初期化し、
        # 対象 stat (attack_bonus) だけ +1 する
        self.weapon.apply_upgrade("attack_bonus", 1)
        self.assertEqual(self.weapon.stats.get("attack_bonus"), 6)
        self.assertEqual(self.weapon.stats.get("crit_rate"), 5)
        self.assertEqual(self.weapon.stats.get("block_chance_close"), 5)
        self.assertEqual(self.weapon.enhance, 6)

        # 新方式の減衰カーブでボーナス計算（1-10回区間）
        # attack_bonus(整数系, growth_room=10): 6回 -> 6 * 0.5 = 3.0
        self.assertAlmostEqual(self.weapon.get_enhance_bonus("attack_bonus"), 3.0)
        # block_chance_close(%系, growth_room=0.10): 5回 -> 5 * (0.10*0.5/10) = 0.025
        self.assertAlmostEqual(self.weapon.get_enhance_bonus("block_chance_close"), 0.025)

    def test_ui_dialog_flow(self):
        from systems.ui import OreSelectionDialog, ParameterSelectionDialog, ConfirmDialog
        from systems.item_handler import make_enhance_callback
        
        # 1. Setup player and items
        player = Player()
        # Give player Iron Sword (only attack/crit stats, no defense or technique stats)
        knife = EquipInstance("weapon", "iron_sword")
        player.weapon_inventory = [knife]
        player.equipped_weapon = knife.iid
        
        # Give player one of each stone in inventory
        player.items = [
            {"key": "red_stone", "count": 1},
            {"key": "blue_stone", "count": 1},
            {"key": "green_stone", "count": 1},
            {"key": "purple_stone", "count": 1},
        ]
        
        # 2. Setup dialogs
        ore_dialog = OreSelectionDialog(800, 600)
        param_dialog = ParameterSelectionDialog(800, 600)
        confirm_dialog = ConfirmDialog(800, 600)
        
        class MockDialog:
            def __init__(self):
                self.text = ""
                self.is_active = False
                
        class MockEnhanceDialog:
            def __init__(self):
                self.is_active = True
                
        msg_dialog = MockDialog()
        enhance_dialog = MockEnhanceDialog()
        
        # Setup real enhance callback on select
        on_select = make_enhance_callback(player, msg_dialog, enhance_dialog)
        
        # Connect everything
        ore_dialog.on_confirm = on_select
        ore_dialog.confirm_dialog = confirm_dialog
        ore_dialog.player_ref = player
        ore_dialog.parameter_selection_dialog = param_dialog
        
        param_dialog.on_confirm = on_select
        param_dialog.confirm_dialog = confirm_dialog
        param_dialog.player_ref = player
        
        # 3. Open dialog for the Iron Sword
        ore_dialog.target_item_data = ("weapon", knife.iid)
        ore_dialog.update_from_player(player)
        
        # 4. Assert that only red_stone is available (plus cancel)
        # because Iron Sword has no defense, technique, or magic stats
        available_keys = [item[0] for item in ore_dialog.available_ores]
        self.assertIn("red_stone", available_keys)
        self.assertNotIn("green_stone", available_keys)
        self.assertNotIn("blue_stone", available_keys)
        self.assertNotIn("purple_stone", available_keys)
        
        # 5. Select red_stone
        red_idx = available_keys.index("red_stone")
        ore_dialog.cursor_idx = red_idx
        ore_dialog.is_active = True
        
        class MockEvent:
            def __init__(self, key):
                self.type = pygame.KEYDOWN
                self.key = key
                
        from constants import KEY_CONFIRM
        # Simulate KEY_CONFIRM event to select the red_stone
        ore_dialog.handle_events([MockEvent(KEY_CONFIRM)])
        
        # Ore dialog should close and Parameter selection dialog should open
        self.assertFalse(ore_dialog.is_active)
        self.assertTrue(param_dialog.is_active)
        
        # Verify available parameters in ParameterSelectionDialog
        # attack_bonus and crit_rate should be present
        param_keys = [item[0] for item in param_dialog.available_params]
        self.assertIn("attack_bonus", param_keys)
        self.assertIn("crit_rate", param_keys)
        self.assertNotIn("block_chance_close", param_keys)
        
        # 6. Select attack_bonus in ParameterSelectionDialog
        atk_idx = param_keys.index("attack_bonus")
        param_dialog.cursor_idx = atk_idx
        
        # Simulate KEY_CONFIRM event to select attack_bonus
        param_dialog.handle_events([MockEvent(KEY_CONFIRM)])
        
        # Parameter dialog should close and Confirm dialog should open
        self.assertFalse(param_dialog.is_active)
        self.assertTrue(confirm_dialog.is_active)
        
        # Verify confirm dialog shows simple confirmation message
        self.assertIn("強化するぜ", confirm_dialog.text)
        
        # 7. Confirm the upgrade in ConfirmDialog
        confirm_dialog.on_yes()
        
        # Red stone should be consumed, purple stone should remain
        self.assertFalse(player.has_item("red_stone"))
        self.assertTrue(player.has_item("purple_stone"))
        
        # Iron Sword stats should be upgraded correctly (only attack_bonus!)
        self.assertEqual(knife.enhance, 1)
        self.assertEqual(knife.stats.get("attack_bonus"), 1)
        self.assertEqual(knife.stats.get("crit_rate"), 0)

if __name__ == "__main__":
    unittest.main()
