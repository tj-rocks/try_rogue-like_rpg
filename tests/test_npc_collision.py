
import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
screen = pygame.display.set_mode((800, 600))

from systems.session_handler import init_ui_elements, start_new_game
from systems.game_state import game_state
from systems.scene_handler import handle_game
from systems.events import active_direction_keys
from constants import KEY_MOVE_LEFT, KEY_MOVE_RIGHT, KEY_MOVE_UP, KEY_MOVE_DOWN

def test_npc_collision():
    print("--- NPC衝突判定テスト開始 ---")
    
    try:
        # 1. 初期化
        ui_elements = init_ui_elements(800, 600)
        player, dungeon = start_new_game(ui_elements, game_state)
        
        # 2. プレイヤーの位置を特定NPCの隣に強制移動
        # 見習い冒険者(@)は P(31, 40) の左上あたりにいるはず
        # 確実にNPCがいる場所に配置する
        target_npc = None
        for npc in dungeon.npcs:
            if npc.name == "見習い冒険者":
                target_npc = npc
                break
        
        if not target_npc:
            print("[SKIP] 見習い冒険者が見つかりませんでした")
            return

        # NPCの右側にプレイヤーを配置
        npc_gx = int(target_npc.x // dungeon.tile_size)
        npc_gy = int(target_npc.y // dungeon.tile_size)
        
        player.x = (npc_gx + 1) * dungeon.tile_size
        player.y = npc_gy * dungeon.tile_size
        player.target_x = player.x
        player.target_y = player.y
        
        initial_px = player.x
        print(f"NPC位置: ({npc_gx}, {npc_gy}), プレイヤー位置: ({player.x // dungeon.tile_size}, {player.y // dungeon.tile_size})")

        # 3. NPCに向かって（左に）移動を試みる
        print("[Step] NPCに向かって移動（左キー）")
        active_direction_keys.clear()
        active_direction_keys.append(KEY_MOVE_LEFT)
        
        # 数フレーム回して移動がブロックされるか確認
        for _ in range(20):
            handle_game(screen, [], player, dungeon, ui_elements, game_state)
            
        # 4. 検証
        print(f"移動後の位置: {player.x // dungeon.tile_size}")
        assert player.x == initial_px, f"NPCをすり抜けました！ (x: {player.x} != {initial_px})"
        
        print("[OK] NPC衝突判定テスト合格！")
        
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    test_npc_collision()
    pygame.quit()
