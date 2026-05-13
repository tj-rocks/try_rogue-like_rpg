
import os
import sys
import pygame
import json

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

# Pygameの初期化
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from systems.data_loader import SAVE_DATA_PATH

def test_save_load_consistency():
    print("--- セーブ＆ロード整合性テスト開始 ---")
    
    # テスト用のパス
    TEST_SAVE_PATH = "tests/test_save_data.json"
    if os.path.exists(TEST_SAVE_PATH):
        os.remove(TEST_SAVE_PATH)

    # 1. プレイヤーの状態をセットアップ
    player = Player()
    player.coin = 1234
    player.hp = 50
    player.attack = 15
    player.add_item_to_inventory("hp_potion", 3)
    player.current_floor = 3
    player.guild_point = 500
    
    # 2. セーブ実行
    player.save_to_file(TEST_SAVE_PATH)
    print(f"[INFO] データをセーブしました: {TEST_SAVE_PATH}")
    
    # 3. 新しいプレイヤーオブジェクトにロード
    new_player = Player()
    success = new_player.load_from_file(TEST_SAVE_PATH)
    
    assert success, "セーブファイルの読み込みに失敗しました"
    print(f"[INFO] データをロードしました")
    
    # 4. 各値が一致するか検証
    assert new_player.coin == 1234, f"所持金が不一致: {new_player.coin}"
    assert new_player.hp == 50, f"HPが不一致: {new_player.hp}"
    assert new_player.attack == 15, f"攻撃力が不一致: {new_player.attack}"
    assert new_player.current_floor == 3, f"現在階層が不一致: {new_player.current_floor}"
    assert new_player.guild_point == 500, f"ギルドポイントが不一致: {new_player.guild_point}"
    
    # アイテム所持数の確認
    potion_count = sum(i["count"] for i in new_player.items if i["key"] == "hp_potion")
    assert potion_count == 3, f"アイテム数が不一致: {potion_count}"

    print("[OK] セーブ＆ロード整合性テスト合格！")
    
    # 後片付け
    if os.path.exists(TEST_SAVE_PATH):
        os.remove(TEST_SAVE_PATH)

if __name__ == "__main__":
    try:
        test_save_load_consistency()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
