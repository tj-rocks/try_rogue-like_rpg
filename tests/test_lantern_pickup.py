import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化 (headless)
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from components.sprites.item import DroppedConsumable
from wordings import Text

def test_lantern_pickup_scenario():
    print("--- カンテラ取得・装備シナリオテスト ---")
    
    # 1. プレイヤーの生成
    player = Player()
    # 初期状態は lantern 'none'
    initial_lantern = player.equipped_lantern
    print(f"初期状態のカンテラ: {initial_lantern}")

    # 2. カンテラアイテムの生成 (basic_lantern)
    # DroppedConsumable(x, y, item_key, item_data)
    from constants import CONSUMABLE_DATA
    lantern_data = CONSUMABLE_DATA.get("basic_lantern")
    if not lantern_data:
        print("❌ エラー: basic_lantern が CONSUMABLE_DATA に見つかりません")
        sys.exit(1)
    
    item_sprite = DroppedConsumable(0, 0, "basic_lantern", lantern_data)

    # 3. アイテム取得実行
    msg = item_sprite.collect(player)
    print(f"取得メッセージ: {msg}")

    # 4. 検証: メッセージに「カンテラ」が含まれているか
    if "カンテラ" not in msg:
        print(f"❌ エラー: メッセージに 'カンテラ' が含まれていません (表示: {msg})")
        sys.exit(1)
    if "basic" in msg:
        print(f"❌ エラー: メッセージに内部キー 'basic' が露出しています (表示: {msg})")
        sys.exit(1)

    # 5. 検証: プレイヤーの装備状態 (自動装備されないこと)
    if player.equipped_lantern is not None:
        print("❌ エラー: カンテラが自動装備されてしまいました")
        sys.exit(1)
    
    # インベントリには入っていることを確認
    lantern_inst = player._find_equip_inst(player.lantern_inventory, player.lantern_inventory[0].iid)
    if not lantern_inst or lantern_inst.key != "basic":
        key = lantern_inst.key if lantern_inst else "None"
        print(f"❌ エラー: インベントリ内のカンテラが 'basic' になっていません (現在: {key})")
        sys.exit(1)
    
    # 6. 検証: 装備インスタンスの名前
    if lantern_inst.get_name() != "カンテラ":
        print(f"❌ エラー: 装備中のカンテラ名が正しくありません (現在: {lantern_inst.get_name()})")
        sys.exit(1)

    # 7. 検証: 視界パラメータが LANTERN_DATA のものと一致するか
    from constants import LANTERN_DATA
    expected_radius = LANTERN_DATA["basic"]["radius"]
    actual_radius = lantern_inst.get_stat("radius")
    if actual_radius != expected_radius:
        print(f"❌ エラー: 視界範囲が一致しません (期待: {expected_radius}, 実際: {actual_radius})")
        sys.exit(1)

    print("✅ カンテラ取得シナリオテスト合格！")

if __name__ == "__main__":
    test_lantern_pickup_scenario()
