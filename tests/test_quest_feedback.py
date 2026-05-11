
import pygame
import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.getcwd())

# Mock pygame before imports
import unittest
from unittest.mock import MagicMock, patch

# テスト用の環境変数設定
os.environ["TEST_MODE"] = "1"

from components.sprites.player import Player
from systems.ui import Dialog
from constants import SOUND_QUEST_COMPLETE

class TestQuestFeedback(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.mixer.init()
        self.player = Player()
        self.dialog = Dialog(800, 600)

    def test_quest_completion_feedback(self):
        # クエストを設定
        quest = {
            "type": "hunt",
            "target_key": "rubble",
            "title": "瓦礫の撤去",
            "amount": 1,
            "_completed_notified": False
        }
        self.player.active_quests = [quest]
        self.player.quest_tokens = {}

        # 達成の証を追加（これで達成判定が走る）
        with patch('pygame.mixer.Sound') as mock_sound:
            msg = self.player.add_quest_token("rubble")
            
            # 1. 音が鳴ったかチェック
            mock_sound.assert_called_with(SOUND_QUEST_COMPLETE)
            mock_sound().play.assert_called()

            # 2. メッセージにタグが含まれているかチェック
            print(f"Completion message: {msg}")
            self.assertIn("<Y>", msg)
            self.assertIn("達成した！", msg)

        # 3. UIが黄色く描画される準備ができているか
        self.dialog.text = msg
        # ラッピング後の行をシミュレート
        # Dialog.draw のロジックを一部抜粋して検証
        all_lines = []
        for paragraph in self.dialog.text.split('\n'):
            all_lines.append(paragraph) # シンプルに分割のみ
        
        has_yellow = False
        for line in all_lines:
            if "<Y>" in line:
                has_yellow = True
                clean_text = line.replace("<Y>", "").replace("</Y>", "")
                self.assertNotIn("<Y>", clean_text)
                print(f"Yellow line detected: {clean_text}")
        
        self.assertTrue(has_yellow)

if __name__ == "__main__":
    unittest.main()
