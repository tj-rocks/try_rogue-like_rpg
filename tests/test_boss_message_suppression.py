
import unittest
from unittest.mock import MagicMock, patch
import os
import sys
from copy import deepcopy

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.sprites.player import Player
from systems.entity_handler import update_dungeon_entities
from systems.dungeon import warp_to_floor
from systems.game_state import game_state

class TestBossMessageSuppression(unittest.TestCase):
    def setUp(self):
        # Pygameの初期化（一部のコンポーネントで必要）
        import pygame
        pygame.init()
        pygame.display.set_mode((1, 1)) # ダミー画面

        self.player = Player()
        self.dungeon = MagicMock()
        self.dungeon.tile_size = 32
        self.dungeon.magic_effects = []
        self.dungeon.dropped_items = []
        self.dungeon.traps = []
        self.dungeon.level = 10
        self.dungeon.current_floor = 10
        self.dungeon.floor_info = {"map": None}
        self.dungeon.is_outbreak = False
        
        # ボスの作成
        self.boss = MagicMock()
        self.boss.is_boss = True
        self.boss.is_dead = False
        self.boss.name = "テストボス"
        self.boss.x = 100
        self.boss.y = 100
        self.boss.width = 32
        self.boss.height = 32
        self.boss.type = "test_boss"
        self.boss.update.return_value = False
        
        self.dungeon.enemies = [self.boss]
        
        # プレイヤーをボスの近くに配置
        self.player.x = 110
        self.player.y = 110
        
        self.dialog = MagicMock()
        self.dialog.is_active = False
        self._game_state_backup = deepcopy(game_state)

    def tearDown(self):
        game_state.clear()
        game_state.update(self._game_state_backup)
        import pygame
        pygame.quit()

    @patch('systems.ui.show_dialog')
    @patch('systems.audio_manager.play_bgm')
    def test_boss_message_shown_only_once_per_floor(self, mock_play_bgm, mock_show_dialog):
        from systems.game_state import game_state
        game_state["is_boss_battle"] = False
        
        # 1. 初回遭遇
        update_dungeon_entities(self.dungeon, self.player, 0.1, self.dialog)
        
        # メッセージが表示されたか確認
        self.assertTrue(mock_show_dialog.called)
        self.assertEqual(self.player.boss_message_shown, True)
        
        # mockをリセット
        mock_show_dialog.reset_mock()
        
        # 2. 同じ階層での2回目以降の遭遇判定
        # (一度離れてまた近づいた状態をシミュレートするために状態をリセット)
        game_state["is_boss_battle"] = False
        update_dungeon_entities(self.dungeon, self.player, 0.1, self.dialog)
        
        # メッセージが表示されないことを確認
        self.assertFalse(mock_show_dialog.called)
        self.assertEqual(self.player.boss_message_shown, True)

    @patch('systems.ui.show_dialog')
    @patch('systems.ui.show_loading_screen')
    def test_boss_message_resets_on_floor_transition(self, mock_load, mock_show_dialog):
        # 1. 10階で遭遇済み
        self.player.boss_message_shown = True
        self.player.current_floor = 10
        
        # 2. 11階へ移動 (warp_to_floor 内でリセットされるはず)
        # 内部で Dungeon クラスが必要なので MagicMock で差し替え
        with patch('systems.dungeon.Dungeon', return_value=self.dungeon):
             warp_to_floor(11, self.player)
        
        # フラグがリセットされているか確認
        self.assertEqual(self.player.current_floor, 11)
        self.assertEqual(self.player.boss_message_shown, False)

    @patch('systems.ui.show_dialog')
    @patch('systems.ui.show_loading_screen')
    def test_boss_message_resets_on_pitfall_warp(self, mock_load, mock_show_dialog):
        # 1. 10階で遭遇済み
        self.player.boss_message_shown = True
        self.player.current_floor = 10
        
        # 2. 落とし穴(warp_with_pitfall)を実行
        from systems.dungeon import warp_with_pitfall
        from systems.game_state import game_state
        game_state["pending_warp"] = None
        warp_with_pitfall(11, self.player)
        
        # 予約が入っていることを確認
        self.assertIsNotNone(game_state["pending_warp"])
        self.assertEqual(game_state["pending_warp"]["floor"], 11)
        
        # 3. scene_handler の挙動をシミュレート (warp_to_floor の呼び出し)
        from systems.dungeon import warp_to_floor
        with patch('systems.dungeon.Dungeon', return_value=self.dungeon):
            w = game_state["pending_warp"]
            warp_to_floor(w["floor"], self.player, spawn_reason=w["spawn_reason"])
        
        # フラグがリセットされているか確認
        self.assertEqual(self.player.current_floor, 11)
        self.assertEqual(self.player.boss_message_shown, False)

    def test_save_load_compatibility(self):
        # 1. boss_message_shown があるデータのロード
        data_with_flg = self.player.to_dict()
        data_with_flg["boss_message_shown"] = True
        self.player.load_dict(data_with_flg)
        self.assertEqual(self.player.boss_message_shown, True)
        
        # 2. boss_message_shown がないデータのロード (既存セーブデータ互換)
        data_no_flg = self.player.to_dict()
        del data_no_flg["boss_message_shown"]
        
        self.player.boss_message_shown = True # 一旦Trueにしてからロード
        self.player.load_dict(data_no_flg)
        self.assertEqual(self.player.boss_message_shown, False) # デフォルト値 False になるはず

    @patch('systems.ui.show_dialog')
    @patch('systems.audio_manager.play_bgm')
    def test_undead_father_defeat_keeps_rank_but_sets_intermediate_ending(self, mock_play_bgm, mock_show_dialog):
        self.player.guild_rank = "S"
        self.player.guild_point = 123

        father = MagicMock()
        father.is_boss = True
        father.is_dead = True
        father.damage_flash_timer = 0
        father.attack_pre_delay_timer = 0
        father.peak_hold_timer = 0
        father.name = "アンデッドの父"
        father.x = 100
        father.y = 100
        father.width = 32
        father.height = 32
        father.type = "undead_father"
        father.drops = {}
        father.normal_drop_rate = 0
        father.rare_drop_rate = 0
        father._log_trace = MagicMock()
        father.update_animation = MagicMock()

        self.dungeon.enemies = [father]

        game_state["post_boss_clear_pending"] = False
        game_state["ending_route"] = "default"
        game_state["is_boss_battle"] = True
        game_state["boss_battle_persistent"] = True
        game_state["boss_encounter_pending"] = True

        update_dungeon_entities(self.dungeon, self.player, 0.1, self.dialog)

        self.assertEqual(self.player.guild_rank, "S")
        self.assertEqual(self.player.guild_point, 123)
        self.assertTrue(game_state["post_boss_clear_pending"])
        self.assertEqual(game_state["ending_route"], "father")

if __name__ == '__main__':
    unittest.main()
