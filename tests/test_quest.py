
import os
import sys
import pygame
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from constants import FIXED_QUEST_DATA

def test_quest_lifecycle():
    print("--- クエスト受注・達成テスト開始 ---")
    
    player = Player()
    
    # 1. 固定クエストから1つ選んで受注する
    if not FIXED_QUEST_DATA:
        print("[SKIP] FIXED_QUEST_DATA が空のためテストをスキップします")
        return
        
    quest = FIXED_QUEST_DATA[0]
    quest_id = quest.get("id")
    target_key = quest.get("target_key")
    amount = quest.get("amount", 1)
    print(f"テストクエスト: {quest.get('title')} (ID: {quest_id}, 対象: {target_key}, 必要数: {amount})")
    
    # 受注処理
    player.accept_quest(quest)
    assert len(player.active_quests) == 1, "クエストが受注されていません"
    assert player.active_quests[0]["id"] == quest_id
    print("[OK] クエスト受注成功")
    
    # 2. 達成条件を満たす
    q_type = quest.get("type")
    if q_type == "hunt":
        # 敵を必要数分倒したことにする（トークン加算）
        for _ in range(amount):
            player.add_quest_token(target_key)
        print(f"[INFO] 敵 '{target_key}' を {amount} 体討伐しました")
    elif q_type == "delivery":
        # アイテムを必要数分入手させる
        player.add_item_to_inventory(target_key, amount)
        print(f"[INFO] アイテム '{target_key}' を {amount} 個入手しました")
    
    # 3. 報告可能かチェック
    is_ready = player.is_quest_reportable(player.active_quests[0])
    assert is_ready == True, f"クエストが達成状態になっていません (Type: {q_type})"
    
    print("[OK] クエスト達成確認成功")

    # 4. クエスト報告（削除）のテスト
    player.remove_quest(player.active_quests[0])
    assert len(player.active_quests) == 0, "クエスト報告後の削除に失敗しました"
    print("[OK] クエスト報告（削除）成功")

    print("[OK] クエスト受注・達成テスト合格！")

if __name__ == "__main__":
    try:
        test_quest_lifecycle()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
