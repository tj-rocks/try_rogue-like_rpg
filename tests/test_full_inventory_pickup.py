import os
import sys
import pygame
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from components.sprites.item import DroppedWeapon
from systems.dungeon import warp_to_floor
from systems.entity_handler import update_dungeon_entities
from systems.ui import Dialog
from constants import MAX_EQUIP_SLOTS, WEAPON_DATA

def test_full_inventory_riding_and_destruction():
    print("--- アイテム乗っかり＆攻撃破壊テスト開始 ---")
    
    # 1. プレイヤーとダンジョンの初期化
    player = Player()
    dungeon = warp_to_floor(1, player, spawn_reason="test")
    
    # 初期位置設定 (2, 2)
    player.x = 64 * 2
    player.y = 64 * 2
    player.prev_x = 64 * 2
    player.prev_y = 64 * 2
    player.target_x = 64 * 2
    player.target_y = 64 * 2
    player.is_moving = False
    
    # 2. 装備インベントリを満タンにする
    player.weapon_inventory = []
    player.armor_inventory = []
    player.shield_inventory = []
    player.accessory_inventory = []
    
    # MAX_EQUIP_SLOTS 分ダミー装備を追加して装備欄を限界にする
    for i in range(MAX_EQUIP_SLOTS):
        player.equip_weapon_by_key("iron_sword")
        
    assert player.get_equipment_count() == MAX_EQUIP_SLOTS
    
    # 3. プレイヤーの1歩先 (3, 2) に落ちている装備アイテムを配置
    dungeon.dropped_items = []
    item = DroppedWeapon(64 * 3, 64 * 2, "iron_sword", WEAPON_DATA["iron_sword"])
    dungeon.dropped_items.append(item)
    
    # ダイアログの初期化
    dialog = Dialog(800, 600)
    dialog.is_active = False
    
    # 4. プレイヤーがアイテムのマスへ移動する (2, 2 -> 3, 2)
    player.prev_x = 64 * 2
    player.prev_y = 64 * 2
    player.x = 64 * 3
    player.y = 64 * 2
    player.target_x = 64 * 3
    player.target_y = 64 * 2
    
    # アイテム取得判定を含むエンティティ更新を実行
    update_dungeon_entities(dungeon, player, 0.1, dialog)
    
    # 検証：
    # - 警告ダイアログが表示されていること
    # - プレイヤーが元の位置 (2, 2) に押し戻されず、アイテムのマス (3, 2) にとどまっていること
    # - last_item_warned_pos に現在の座標 (3, 2) が記録されていること
    print(f"ダイアログ状態: active={dialog.is_active}, text='{dialog.text}'")
    print(f"プレイヤー座標: x={player.x}, y={player.y}")
    assert dialog.is_active == True, "インベントリ満タン時に警告ダイアログが表示されていません"
    assert "装備がいっぱいで" in dialog.text, f"警告文言が正しくありません: {dialog.text}"
    assert player.x == 64 * 3 and player.y == 64 * 2, f"プレイヤーが押し戻されています (x={player.x}, y={player.y})"
    assert player.last_item_warned_pos == (3, 2), f"last_item_warned_pos が記録されていません: {player.last_item_warned_pos}"
    
    # 5. そのマスで次のターンを経過させる (静止状態)
    # ダイアログを閉じた状態にする
    dialog.is_active = False
    
    player.prev_x = 64 * 3
    player.prev_y = 64 * 2
    # 座標は動かない状態で更新
    update_dungeon_entities(dungeon, player, 0.1, dialog)
    
    # 検証：同じマスに留まっている間は、警告ダイアログが再表示されないこと
    assert dialog.is_active == False, "同じマスに留まっているのにもかかわらず警告ダイアログが再表示されました"
    
    # 6. 一度離れてから、再びそのマスに入る
    # 別のマスへ移動 (2, 2 に戻る)
    player.x = 64 * 2
    player.y = 64 * 2
    player.target_x = 64 * 2
    player.target_y = 64 * 2
    update_dungeon_entities(dungeon, player, 0.1, dialog)
    
    # この時点で last_item_warned_pos はリセットされるはず
    assert player.last_item_warned_pos is None, f"移動したのに last_item_warned_pos がクリアされていません: {player.last_item_warned_pos}"
    
    # 再びアイテムのマス (3, 2) へ移動
    player.prev_x = 64 * 2
    player.prev_y = 64 * 2
    player.x = 64 * 3
    player.y = 64 * 2
    player.target_x = 64 * 3
    player.target_y = 64 * 2
    update_dungeon_entities(dungeon, player, 0.1, dialog)
    
    # 検証：再び乗り直したときは警告ダイアログが表示されること
    assert dialog.is_active == True, "アイテムに乗り直したのに警告ダイアログが表示されていません"
    assert "装備がいっぱいで" in dialog.text
    
    # 7. 攻撃によってアイテムが誤って破壊されないことを確認
    # プレイヤーを (2, 2) に配置し、右方向 (right) を向かせる
    player.x = 64 * 2
    player.y = 64 * 2
    player.prev_x = 64 * 2
    player.prev_y = 64 * 2
    player.target_x = 64 * 2
    player.target_y = 64 * 2
    player.facing = "right"
    
    # (3, 2) にアイテムが落ちている状態を維持
    dungeon.dropped_items = [item]
    item.is_collected = False
    
    dialog.is_active = False
    dialog.text = ""
    
    # 攻撃実行 (右方向に向かって)
    player._execute_strike(dungeon, dialog)
    
    # 検証：アイテムが破壊されずに残っていること
    print(f"攻撃後のアイテムリスト: {dungeon.dropped_items}")
    assert len(dungeon.dropped_items) == 1, "攻撃によってアイテムが誤って破壊されてしまいました"
    assert "破壊した！" not in dialog.text, "破壊ログが表示されています"
    
    print("✅ アイテム乗っかり＆非破壊の検証合格！")

if __name__ == "__main__":
    test_full_inventory_riding_and_destruction()
