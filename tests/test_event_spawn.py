import os
import sys
import pygame
import math

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["TEST_MODE"] = "1"
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from systems.dungeon import warp_to_floor

def test_furthest_room_spawn():
    print("--- 昇級証の最奥配置テスト開始 ---")
    
    player = Player()
    # Fランク昇格クエスト（冒険者の証回収）を受注している状態にする
    player.active_quests.append({
        "id": "rank_up_F",
        "type": "delivery",
        "is_rank_up": True,
        "target_key": "adventurer_proof"
    })

    # 冒険者の証がドロップする 5階 へワープ
    dungeon = warp_to_floor(5, player, spawn_reason="test")

    # 1. 上り階段の位置を取得
    up_stairs = None
    for r in range(dungeon.map_height):
        for c in range(dungeon.map_width):
            if dungeon.map_data[r][c] == 2:
                up_stairs = (c, r)
                break
        if up_stairs: break
        
    if not up_stairs:
        up_stairs = (int((player.x + dungeon.tile_size / 2) // dungeon.tile_size), 
                     int((player.y + dungeon.tile_size / 2) // dungeon.tile_size))

    # 2. 全部屋の中で上り階段から一番遠い部屋（中心座標）を特定
    expected_furthest_room = None
    max_dist = -1
    for rx, ry in dungeon.rooms:
        dist = (rx - up_stairs[0])**2 + (ry - up_stairs[1])**2
        if dist > max_dist:
            max_dist = dist
            expected_furthest_room = (rx, ry)

    # 3. 冒険者の証を探す
    found_item = None
    for item in dungeon.dropped_items:
        if getattr(item, "item_key", None) == "adventurer_proof":
            found_item = item
            break
            
    assert found_item is not None, "冒険者の証がドロップしていません！"
    
    gx, gy = int(found_item.x // dungeon.tile_size), int(found_item.y // dungeon.tile_size)
    print(f"[OK] 冒険者の証を発見！ 位置: ({gx}, {gy})")
    
    # 4. 見つかった位置が「一番遠い部屋」の周辺(3x3程度)にあるかを検証
    dist_to_expected = max(abs(gx - expected_furthest_room[0]), abs(gy - expected_furthest_room[1]))
    assert dist_to_expected <= 2, f"アイテムが最奥の部屋({expected_furthest_room})から離れた位置({gx}, {gy})に落ちています！"
    
    print(f"[OK] 冒険者の証が上り階段から一番遠い部屋の中心付近に配置されていることを確認")
    print("--- テスト合格 ---")

if __name__ == "__main__":
    try:
        test_furthest_room_spawn()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
