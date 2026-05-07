import sys
import os

# プロジェクトのルートをパスに追加
sys.path.append(os.getcwd())

import pygame
pygame.init()

# 必要なモジュールをインポート
from components.sprites.player import Player
from systems.ui import GuildDialog
from wordings import Text

def test_quest_logic():
    print("=== Quest ID Logic Test ===")
    
    player = Player()
    # ダミーのダンジョン参照
    class DummyDungeon:
        def __init__(self):
            class DummyGuild:
                def get_next_rank_data(self, rank):
                    return {"rank": "E", "required_gp": 100, "rank_up_item": "adventurer_cert_e"}
            self.guild_system = DummyGuild()
    
    dungeon = DummyDungeon()
    guild_dialog = GuildDialog(800, 600)
    
    print("\n1. Testing Rank-Up Quest ID Generation...")
    rank_up_data = dungeon.guild_system.get_next_rank_data("F")
    # _create_rank_up_quest は内部メソッドなので直接テスト
    q = guild_dialog._create_rank_up_quest(rank_up_data)
    
    print(f"Generated Quest: {q['title']}")
    print(f"ID: {q.get('id')}")
    
    if q.get("id") == "rank_up_E":
        print("[PASS] Rank-up quest has correct ID.")
    else:
        print("[FAIL] Rank-up quest ID is missing or incorrect.")
        return

    print("\n2. Testing accept_quest (empty list)...")
    player.accept_quest(q)
    if len(player.active_quests) == 1 and player.active_quests[0]["id"] == "rank_up_E":
        print("[PASS] Quest accepted successfully.")
    else:
        print("[FAIL] Quest not accepted.")
        return

    print("\n3. Testing accept_quest (blocking overwrite)...")
    q2 = {"id": "normal_quest", "title": "Normal Quest"}
    player.accept_quest(q2)
    if len(player.active_quests) == 1 and player.active_quests[0]["id"] == "rank_up_E":
        print("[PASS] Overwrite blocked as expected (only 1 quest allowed).")
    else:
        print("[FAIL] Overwrite was not blocked or failed.")
        return

    print("\n4. Testing remove_quest via ID...")
    # remove_quest はオブジェクト一致で消すが、IDが一致していることが重要
    target_q = player.active_quests[0]
    player.remove_quest(target_q)
    if len(player.active_quests) == 0:
        print("[PASS] Quest removed successfully.")
    else:
        print("[FAIL] Quest removal failed.")
        return

    print("\nAll Tests Passed!")

if __name__ == "__main__":
    try:
        test_quest_logic()
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
