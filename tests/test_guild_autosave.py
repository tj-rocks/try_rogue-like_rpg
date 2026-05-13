import os
import sys
import pygame
import time

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# [IMPORTANT] テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

from components.sprites.player import Player
from systems.ui import GuildDialog
from unittest.mock import MagicMock

def test_guild_autosave_on_completion():
    print("\n--- ギルドクエスト達成時自動セーブテスト ---")
    
    # Pygame初期化（ヘッドレス）
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    pygame.init()
    pygame.display.set_mode((1, 1))
    
    # 1. 準備: プレイヤーと納品クエスト
    player = Player()
    player.coin = 0
    player.guild_point = 0
    
    target_key = "hp_potion"
    quest = {
        "id": "test_quest_1",
        "type": "delivery",
        "target_key": target_key,
        "target_name": "回復薬",
        "amount": 1,
        "reward_gold": 100,
        "reward_gp": 10,
        "title": "テスト用納品依頼"
    }
    player.active_quests = [quest]
    player.items = [{"key": target_key, "count": 1}]
    
    # 2. 保存ファイルの初期状態（存在すれば削除）
    from systems.data_loader import SAVE_DATA_PATH
    if os.path.exists(SAVE_DATA_PATH):
        os.remove(SAVE_DATA_PATH)
    
    # 3. ギルドダイアログを介して達成報告を実行
    # 必要なモックを作成
    guild_dialog = GuildDialog(1200, 900)
    mock_dialog = MagicMock()
    mock_dialog.is_active = False
    
    print(f"[TEST] クエスト報告実行: {quest['title']}")
    # _report_quest を直接叩く
    guild_dialog._report_quest(player, quest, mock_dialog)
    
    # 4. 検証: セーブファイルが作成されているか
    assert os.path.exists(SAVE_DATA_PATH), "クエスト達成後にセーブファイルが作成されていません"
    
    # 5. 検証: セーブファイルの中身が正しいか（報酬が反映されているか）
    import json
    with open(SAVE_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"[TEST] 保存データ確認: coin={data.get('coin')}, gp={data.get('guild_point')}")
    assert data.get("coin") == 100, f"所持金が保存されていません (Expected: 100, Got: {data.get('coin')})"
    assert data.get("guild_point") == 10, f"GPが保存されていません (Expected: 10, Got: {data.get('guild_point')})"
    assert len(data.get("active_quests", [])) == 0, "達成したクエストがリストに残っています"
    
    print("✅ ギルドクエスト達成時自動セーブテスト合格！")

if __name__ == "__main__":
    try:
        test_guild_autosave_on_completion()
        pygame.quit()
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
