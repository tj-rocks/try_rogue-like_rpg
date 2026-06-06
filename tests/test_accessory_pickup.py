import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

# Pygameの初期化 (headless)
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from components.sprites.item import DroppedAccessory
from wordings import Text

def test_accessory_pickup_scenario():
    print("--- アクセサリ取得・装備シナリオテスト ---")
    
    # 1. プレイヤーの生成
    player = Player()
    # 初期状態は装備なし
    initial_equipped = player.equipped_accessory
    print(f"初期状態のアクセサリ: {initial_equipped}")

    # 2. アクセサリアイテムの生成 (luminous_gem)
    from constants import ACCESSORY_DATA
    accessory_data = ACCESSORY_DATA.get("luminous_gem")
    if not accessory_data:
        print("❌ エラー: luminous_gem が ACCESSORY_DATA に見つかりません")
        sys.exit(1)
    
    item_sprite = DroppedAccessory(0, 0, "luminous_gem", accessory_data)

    # 3. アイテム取得実行
    msg = item_sprite.collect(player)
    print(f"取得メッセージ: {msg}")

    # 4. 検証: メッセージに「光る指輪」が含まれているか
    if "光る指輪" not in msg:
        print(f"❌ エラー: メッセージに '光る指輪' が含まれていません (表示: {msg})")
        sys.exit(1)

    # 5. 検証: プレイヤーの装備状態 (自動装備されないこと)
    if player.equipped_accessory is not None:
        print("❌ エラー: アクセサリが自動装備されてしまいました")
        sys.exit(1)
    
    # インベントリには入っていることを確認
    if not player.accessory_inventory:
        print("❌ エラー: インベントリにアクセサリが追加されていません")
        sys.exit(1)

    accessory_inst = player._find_equip_inst(player.accessory_inventory, player.accessory_inventory[0].iid)
    if not accessory_inst or accessory_inst.key != "luminous_gem":
        key = accessory_inst.key if accessory_inst else "None"
        print(f"❌ エラー: インベントリ内のアクセサリが 'luminous_gem' になっていません (現在: {key})")
        sys.exit(1)
    
    # 6. 検証: 装備インスタンスの名前
    if accessory_inst.get_name() != "光る指輪":
        print(f"❌ エラー: アクセサリ名が正しくありません (現在: {accessory_inst.get_name()})")
        sys.exit(1)

    # 装備前のステータス記録
    base_hp = player.max_hp
    base_def = player.total_defense
    base_vision = player.lantern_bonus

    # 装備してみる
    player.change_accessory(accessory_inst.iid)
    if player.equipped_accessory != accessory_inst.iid:
        print("❌ エラー: アクセサリの装備変更に失敗しました")
        sys.exit(1)

    # 7. 検証: 装備効果（ステータス・視界）が正しく反映されているか
    expected_hp_bonus = accessory_data.get("hp_bonus", 0)
    expected_def_bonus = accessory_data.get("defense_bonus", 0)
    expected_vision_bonus = accessory_data.get("lantern_bonus", 0)

    if player.max_hp != base_hp + expected_hp_bonus:
        print(f"❌ エラー: HPボーナスが適用されていません (期待: {base_hp + expected_hp_bonus}, 実際: {player.max_hp})")
        sys.exit(1)

    if player.total_defense != base_def + expected_def_bonus:
        print(f"❌ エラー: 防御力ボーナスが適用されていません (期待: {base_def + expected_def_bonus}, 実際: {player.total_defense})")
        sys.exit(1)

    if player.lantern_bonus != base_vision + expected_vision_bonus:
        print(f"❌ エラー: 視界ボーナスが適用されていません (期待: {base_vision + expected_vision_bonus}, 実際: {player.lantern_bonus})")
        sys.exit(1)

    print("✅ アクセサリ取得シナリオテスト合格！")

if __name__ == "__main__":
    test_accessory_pickup_scenario()
