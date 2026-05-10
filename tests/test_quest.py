
import os
import sys
import pygame
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["TEST_MODE"] = "1"
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


def test_quest_generation_integrity():
    """GuildSystem が生成するクエストに必須フィールドが必ず含まれることを確認する"""
    print("--- クエスト生成データ整合性テスト開始 ---")
    from systems.guild import GuildSystem

    player = Player()
    player.guild_rank = "F"
    guild = GuildSystem()

    # 複数回生成してすべてのクエストを検査
    REQUIRED_FIELDS = ["type", "target_key", "title", "amount", "reward_gold", "reward_gp"]
    for trial in range(10):
        guild.generate_quests(player)
        all_quests = guild.available_quests + guild.fixed_quests
        assert len(all_quests) > 0, f"Trial {trial}: クエストが1件も生成されませんでした"
        
        for q in all_quests:
            for field in REQUIRED_FIELDS:
                assert field in q, f"Trial {trial}: クエスト '{q.get('title', '不明')}' に必須フィールド '{field}' がありません"
            assert q["reward_gold"] >= 1, f"Trial {trial}: reward_gold が 0 以下です: {q}"
            assert q["reward_gp"] >= 1, f"Trial {trial}: reward_gp が 0 以下です: {q}"
            assert q["target_key"], f"Trial {trial}: target_key が空です: {q}"

    print(f"[OK] 10回の生成で全クエストの必須フィールドを確認しました")
    print("[OK] クエスト生成データ整合性テスト合格！")


def test_fixed_quest_integrity():
    """固定クエスト(FIXED_QUEST_DATA)のマスターデータに必須フィールドが揃っていることを確認する"""
    print("--- 固定クエストマスターデータ整合性テスト開始 ---")

    if not FIXED_QUEST_DATA:
        print("[SKIP] FIXED_QUEST_DATA が空のためスキップします")
        return

    REQUIRED_FIELDS = ["id", "type", "target_key", "title", "amount", "reward_gold", "reward_gp"]
    for q in FIXED_QUEST_DATA:
        for field in REQUIRED_FIELDS:
            assert field in q, f"固定クエスト '{q.get('id', '不明')}' に必須フィールド '{field}' がありません"
        assert q["reward_gold"] >= 1, f"固定クエスト '{q['id']}' の reward_gold が 0 以下です"
        assert q["reward_gp"] >= 1, f"固定クエスト '{q['id']}' の reward_gp が 0 以下です"
        assert q["target_key"], f"固定クエスト '{q['id']}' の target_key が空です"
        print(f"  [OK] {q['id']}: reward_gold={q['reward_gold']}, reward_gp={q['reward_gp']}, target_key={q['target_key']}")

    print("[OK] 固定クエストマスターデータ整合性テスト合格！")


if __name__ == "__main__":
    try:
        test_quest_lifecycle()
        test_quest_generation_integrity()
        test_fixed_quest_integrity()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
