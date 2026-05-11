
import os
import sys
import unittest
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化（ダミードライバ）
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["TEST_MODE"] = "1"
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player, StaveInstance, EquipInstance
from systems.ui import GuildDialog

class TestGuildReporting(unittest.TestCase):
    def setUp(self):
        self.player = Player()
        self.player.active_quests = []
        self.player.items = []
        self.player.stave_inventory = []
        self.player.weapon_inventory = []
        self.player.armor_inventory = []
        self.player.shield_inventory = []
        self.player.lantern_inventory = []
        self.player.equipped_weapon = None
        self.player.equipped_armor = None
        self.player.equipped_shield = None
        self.player.equipped_lantern = None
        self.player.weapon = None
        
        # GuildDialogのモック
        self.guild_dialog = GuildDialog(1200, 900)
        self.guild_dialog.dungeon_ref = MagicMock()
        # guild_system のモック
        self.guild_dialog.dungeon_ref.guild_system = MagicMock()
        self.guild_dialog.dungeon_ref.guild_system.get_next_rank_data.return_value = None
        
        self.guild_dialog._play_placeholder_complete_sound = MagicMock()
        
        # メッセージ用ダイアログのモック
        self.message_dialog = MagicMock()
        self.message_dialog.text = ""
        self.message_dialog.is_active = False

    def test_report_stave_delivery(self):
        """杖の納品依頼が正しく報告（達成）できることをテスト"""
        target_key = "fire_stave"
        quest = {
            "id": "test_stave_q",
            "type": "delivery",
            "target_key": target_key,
            "amount": 1,
            "title": "火炎の杖の納品",
            "reward_gold": 100,
            "reward_gp": 5
        }
        self.player.active_quests.append(quest)
        
        # プレイヤーに杖を持たせる
        stave = StaveInstance(target_key)
        self.player.stave_inventory.append(stave)
        
        # 報告前
        self.assertEqual(len(self.player.active_quests), 1)
        self.assertEqual(len(self.player.stave_inventory), 1)
        
        # 報告実行
        self.guild_dialog._report_quest(self.player, quest, self.message_dialog)
        
        # 報告後：クエストが削除され、杖も消費されているはず
        self.assertEqual(len(self.player.active_quests), 0, "クエストが削除されていません")
        self.assertEqual(len(self.player.stave_inventory), 0, "杖が消費されていません")
        self.assertTrue(self.message_dialog.is_active, "達成メッセージが表示されていません")
        self.assertIn("依頼を達成しました", self.message_dialog.text)
        
        # モードが AUTO_REPORT になっているはず
        self.assertEqual(self.guild_dialog.mode, "AUTO_REPORT")
        self.assertEqual(len(self.guild_dialog.items), 1)
        self.assertEqual(self.guild_dialog.items[0][0], "auto_report")

    def test_report_hunt_quest(self):
        """討伐依頼が正しく報告（達成）できることをテスト"""
        target_key = "slime"
        quest = {
            "id": "test_hunt_q",
            "type": "hunt",
            "target_key": target_key,
            "amount": 3,
            "title": "スライム討伐",
            "reward_gold": 50,
            "reward_gp": 3
        }
        self.player.active_quests.append(quest)
        
        # 討伐数を稼ぐ
        self.player.quest_tokens[target_key] = 3
        
        # 報告実行
        self.guild_dialog._report_quest(self.player, quest, self.message_dialog)
        
        # 報告後
        self.assertEqual(len(self.player.active_quests), 0)
        self.assertEqual(self.player.quest_tokens[target_key], 0, "討伐トークンが消費されていません")
        self.assertTrue(self.message_dialog.is_active)
        self.assertEqual(self.guild_dialog.mode, "AUTO_REPORT")

    def test_equipped_item_not_reportable(self):
        """装備中のアイテムは納品対象外（報告不可）であることをテスト"""
        target_key = "iron_sword"
        quest = {
            "id": "test_equip_q",
            "type": "delivery",
            "target_key": target_key,
            "amount": 1,
            "title": "鉄の剣の納品"
        }
        self.player.active_quests.append(quest)
        
        # 武器を1つ持たせて装備する
        inst = EquipInstance("weapon", target_key)
        self.player.weapon_inventory.append(inst)
        self.player.equipped_weapon = inst.iid
        
        # 判定チェック：装備中なので報告不可（False）であるべき
        self.assertFalse(self.player.is_quest_reportable(quest), "装備中のアイテムが納品対象に含まれています")

    def test_report_prioritizes_unequipped(self):
        """同じアイテムが複数ある場合、未装備のものが優先的に納品されることをテスト"""
        target_key = "iron_sword"
        quest = {
            "id": "test_priority_q",
            "type": "delivery",
            "target_key": target_key,
            "amount": 1,
            "title": "鉄の剣の納品",
            "reward_gold": 100, "reward_gp": 5
        }
        self.player.active_quests.append(quest)
        
        # 武器を2つ持たせ、1つだけ装備する
        inst_equipped = EquipInstance("weapon", target_key)
        inst_spare = EquipInstance("weapon", target_key)
        self.player.weapon_inventory.append(inst_equipped)
        self.player.weapon_inventory.append(inst_spare)
        self.player.equipped_weapon = inst_equipped.iid
        
        # 判定チェック：スペア（未装備）があるので報告可能（True）
        self.assertTrue(self.player.is_quest_reportable(quest))
        
        # 報告実行
        self.guild_dialog._report_quest(self.player, quest, self.message_dialog)
        
        # 報告後：1つ消費されているが、装備中のインスタンスが残っているべき
        self.assertEqual(len(self.player.weapon_inventory), 1, "アイテムが正しく1つ消費されていません")
        self.assertEqual(self.player.weapon_inventory[0].iid, inst_equipped.iid, "装備中のアイテムが優先的に消費されてしまいました")
        self.assertEqual(self.player.equipped_weapon, inst_equipped.iid, "装備が解除されてしまいました")

    def test_report_cancel_suppresses_auto_report(self):
        """報告をキャンセル（または「いいえ」）した際、自動報告が抑制されることをテスト"""
        target_key = "iron_sword"
        quest = {"id": "q1", "type": "delivery", "target_key": target_key, "amount": 1, "title": "T"}
        self.player.active_quests.append(quest)
        self.player.weapon_inventory.append(EquipInstance("weapon", target_key))
        
        # 1. 初期状態：MENUモードのままで、_pending_report がセットされるはず
        self.guild_dialog.setup(self.player, self.guild_dialog.dungeon_ref)
        self.assertEqual(self.guild_dialog.mode, "MENU")
        self.assertIsNotNone(self.guild_dialog._pending_report)
        
        # 2. キャンセル操作（いいえ）をシミュレート
        self.guild_dialog._pending_report = None
        self.guild_dialog._skip_auto_report = True
        self.guild_dialog.setup(self.player, self.guild_dialog.dungeon_ref)
        
        # 3. 再度setupしても、フラグによりMENUのまま（_pending_reportも無し）のはず
        self.assertEqual(self.guild_dialog.mode, "MENU")
        self.assertIsNone(self.guild_dialog._pending_report, "キャンセル後も報告待ちが残っています")
        
        # 4. ダイアログを一度閉じて開く操作をシミュレート
        self.guild_dialog.is_active = False # 一度閉じる
        self.guild_dialog.is_active = True  # 再び開く（ここでフラグがリセットされる）
        self.guild_dialog.setup(self.player, self.guild_dialog.dungeon_ref)
        # 5. 再び開いた後は、報告待ちが復活しているはず
        self.assertIsNotNone(self.guild_dialog._pending_report, "ダイアログ再起動後に報告待ちが復帰していません")

    def test_manual_report_requires_confirmation(self):
        """手動での報告時（status=='active'）に確認ダイアログが表示されることをテスト"""
        quest = {"id": "q_manual", "type": "hunt", "target_key": "slime", "amount": 1, "title": "T"}
        self.player.active_quests.append(quest)
        self.player.quest_tokens["slime"] = 1
        
        # アイテムリストを構築
        self.guild_dialog.mode = "REPORT"
        self.guild_dialog.setup(self.player, self.guild_dialog.dungeon_ref)
        # items = [("active", quest), ("back", ...)]
        
        # 決定キーで実行をシミュレート
        confirm_dialog = MagicMock()
        confirm_dialog.is_active = False
        self.guild_dialog.cursor_idx = 0
        self.guild_dialog.execute_quest(self.player, self.message_dialog, confirm_dialog)
        
        # 確認ダイアログがアクティブになり、即座に報告は実行されないはず
        self.assertTrue(confirm_dialog.is_active, "手動報告で確認ダイアログが表示されていません")
        self.assertEqual(len(self.player.active_quests), 1, "確認前にクエストが削除されてしまいました")

    def test_hunt_auto_report_generic_text(self):
        """討伐依頼の自動報告時、汎用の確認テキストが表示されることをテスト"""
        from wordings import Text
        quest = {"id": "q_hunt", "type": "hunt", "target_key": "slime", "amount": 1, "title": "T"}
        self.player.active_quests.append(quest)
        self.player.quest_tokens["slime"] = 1
        
        self.guild_dialog.is_active = True
        self.guild_dialog.setup(self.player, self.guild_dialog.dungeon_ref)
        self.assertEqual(self.guild_dialog._pending_report, quest)
        
        confirm_dialog = MagicMock()
        confirm_dialog.is_active = False
        
        # handle_events を呼んで確認ダイアログを表示させる
        self.guild_dialog.handle_events([], self.player, self.message_dialog, confirm_dialog)
        
        self.assertTrue(confirm_dialog.is_active)
        self.assertEqual(confirm_dialog.text, Text.UI.GUILD_REPORT_CONFIRM_GENERIC)



if __name__ == "__main__":
    unittest.main()
