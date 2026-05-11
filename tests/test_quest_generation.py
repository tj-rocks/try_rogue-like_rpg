
import os
import sys
import unittest

# プロジェクトルートをパスに追加
sys.path.append(os.getcwd())

# テスト用の環境変数設定
os.environ["TEST_MODE"] = "1"

from systems.guild import GuildSystem
from wordings import Text

class TestQuestGeneration(unittest.TestCase):
    def setUp(self):
        # 簡易的なダンジョン参照用モック
        self.mock_dungeon = type('obj', (object,), {
            'guild_system': None
        })
        self.guild = GuildSystem()

    def test_random_quest_fields(self):
        # 100回生成して、すべてのクエストに新しいフィールドが含まれているか確認
        for _ in range(100):
            # ランクFの討伐クエストを生成
            q = self.guild._generate_hunt_quest(["F"], 1.0, 1, 3)
            if q:
                self.assertIn("description", q, "Quest should have a description field")
                self.assertIn("requester", q, "Quest should have a requester field")
                
                self.assertTrue(len(q["description"]) > 0, "Description should not be empty")
                self.assertTrue(len(q["requester"]) > 0, "Requester should not be empty")
                
                # 依頼主がNPCリストかその他リストのどちらかに含まれていることを確認
                all_possible_requesters = Text.Guild.QUEST_REQUESTER_NPCS + Text.Guild.QUEST_REQUESTER_OTHERS
                self.assertIn(q["requester"], all_possible_requesters, f"Requester '{q['requester']}' must be in predefined lists")
                
                print(f"Generated Quest: [{q['requester']}] {q['title']} - {q['description']}")

    def test_delivery_quest_fields(self):
        # 納品クエストについても同様に確認
        for _ in range(50):
            q = self.guild._generate_delivery_quest(["F"], 1.0, 1, 3)
            if q:
                self.assertIn("description", q)
                self.assertIn("requester", q)
                self.assertTrue(len(q["description"]) > 0)
                self.assertTrue(len(q["requester"]) > 0)

if __name__ == "__main__":
    unittest.main()
