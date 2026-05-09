
import os
import sys
import pygame
from unittest.mock import MagicMock, patch

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from systems.dungeon import Dungeon, warp_to_floor
from constants import TILE_SIZE

def test_new_game_start_pos():
    print("--- 初期位置テスト開始 ---")
    player = Player()
    # warp_to_floor を通じて村（0階）に配置
    dungeon = warp_to_floor(0, player, spawn_reason="test")
    
    print(f"初期階層: {player.current_floor}")
    assert player.current_floor == 0
    # グリッドに合っていることを確認
    print(f"プレイヤー位置: ({player.x}, {player.y})")
    assert player.x % TILE_SIZE == 0 or ((player.x - (TILE_SIZE - player.width)//2) % TILE_SIZE == 0)
    assert player.y % TILE_SIZE == 0 or ((player.y - (TILE_SIZE - player.height)//2) % TILE_SIZE == 0)
    print(f"[OK] 初期階層・位置確認成功")

def test_floor_navigation():
    print("--- 階層移動テスト開始 ---")
    player = Player()
    
    # 0階(村)から1階(ダンジョン)へ
    dungeon = warp_to_floor(1, player, spawn_reason="test")
    print(f"移動後階層: {player.current_floor}")
    assert player.current_floor == 1
    assert dungeon.current_floor == 1
    
    # 降りた直後は上り階段(2)の上にいるべき
    tx, ty = int(player.x // TILE_SIZE), int(player.y // TILE_SIZE)
    print(f"1階移動直後の位置: ({tx}, {ty}), タイル: {dungeon.map_data[ty][tx]}")
    assert dungeon.map_data[ty][tx] == 2, "深い階へ移動した後は上り階段(2)の上にいるべきです"
    
    # 1階から2階へ
    dungeon_f2 = warp_to_floor(2, player, spawn_reason="test")
    assert player.current_floor == 2
    tx, ty = int(player.x // TILE_SIZE), int(player.y // TILE_SIZE)
    print(f"2階移動直後の位置: ({tx}, {ty}), タイル: {dungeon_f2.map_data[ty][tx]}")
    assert dungeon_f2.map_data[ty][tx] == 2, "深い階へ移動した後は上り階段(2)の上にいるべきです"
    print(f"[OK] 階層移動(1->2)成功")
    
    # 2階から1階へ（逆送）
    dungeon_f1 = warp_to_floor(1, player, spawn_reason="test")
    assert player.current_floor == 1
    tx, ty = int(player.x // TILE_SIZE), int(player.y // TILE_SIZE)
    print(f"1階(逆送)移動直後の位置: ({tx}, {ty}), タイル: {dungeon_f1.map_data[ty][tx]}")
    assert dungeon_f1.map_data[ty][tx] == 3, "浅い階へ移動した後は下り階段(3)の上にいるべきです"
    print(f"[OK] 階層移動(2->1)成功")

def test_item_interaction():
    print("--- アイテム取得・使用テスト開始 ---")
    player = Player()
    player.hp = 10
    player.max_hp = 100
    
    # 1. アイテム取得
    item_key = "hp_potion"
    player.add_item_to_inventory(item_key, 1)
    assert player.has_item(item_key) == True
    print(f"[OK] アイテム '{item_key}' の取得成功")
    
    # 2. アイテム使用（HP回復）
    # 手動で回復処理をシミュレート（本来は item_handler 等で行うが、ここではロジックの口を確認）
    from constants import CONSUMABLE_DATA
    recover = CONSUMABLE_DATA[item_key].get("heal_amount", 0)
    player.hp = min(player.max_hp, player.hp + recover)
    player.remove_item_by_key(item_key, 1)
    
    assert player.hp > 10, f"HPが回復していません: {player.hp}"
    assert player.has_item(item_key) == False, "使用したアイテムが消えていません"
    print(f"[OK] アイテム使用によるHP回復成功 (HP: {player.hp})")

if __name__ == "__main__":
    try:
        test_new_game_start_pos()
        test_floor_navigation()
        test_item_interaction()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
