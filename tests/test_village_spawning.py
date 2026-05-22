import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

# Pygameの初期化（ヘッドレス）
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
screen = pygame.display.set_mode((800, 600))

from systems.session_handler import init_ui_elements, start_new_game
from systems.game_state import game_state

def test_village_spawning():
    print("--- 街のNPC＆障害物配置 自動テスト開始 ---")
    
    try:
        # 1. 初期化
        ui_elements = init_ui_elements(800, 600)
        player, dungeon = start_new_game(ui_elements, game_state)
        
        # 2. 基本的な配置検証
        assert len(dungeon.npcs) > 0, "NPCが1人も配置されていません！"
        assert len(dungeon.enemies) > 0, "障害物・エネミーが1つも配置されていません！"
        
        print(f"・総NPC数: {len(dungeon.npcs)}")
        print(f"・総障害物数: {len(dungeon.enemies)}")
        
        # 3. 代表的な主要NPCが正しくスポンしているかの検証 (ロジック共通のため代表として武器屋で検証)
        expected_npcs = ["武器屋"]
        
        spawned_npc_names = [npc.name for npc in dungeon.npcs]
        for name in expected_npcs:
            assert name in spawned_npc_names, f"主要NPC '{name}' が配置されていません！"
            print(f"  - OK: NPC '{name}' の配置を確認")
            
        # 4. 特定の主要障害物が正しくスポンしているかの検証
        # dungeon.enemies内の障害物のIDをチェック
        spawned_obstacle_ids = [e.type for e in dungeon.enemies]
        expected_obstacles = ["wood_barrel", "crate", "pot", "rubble", "anvil"]
        for o_id in expected_obstacles:
            assert o_id in spawned_obstacle_ids, f"主要障害物 '{o_id}' が配置されていません！"
            print(f"  - OK: 障害物 '{o_id}' の配置を確認")
            
        # 5. すべてのNPCと障害物がマップ座標の範囲内にいることの検証
        for npc in dungeon.npcs:
            gx = npc.x // dungeon.tile_size
            gy = npc.y // dungeon.tile_size
            assert 0 <= gx < dungeon.map_width, f"NPC '{npc.name}' がマップ範囲外です！ x: {gx}"
            assert 0 <= gy < dungeon.map_height, f"NPC '{npc.name}' がマップ範囲外です！ y: {gy}"
            
        for obs in dungeon.enemies:
            gx = obs.x // dungeon.tile_size
            gy = obs.y // dungeon.tile_size
            assert 0 <= gx < dungeon.map_width, f"障害物 '{obs.type}' がマップ範囲外です！ x: {gx}"
            assert 0 <= gy < dungeon.map_height, f"障害物 '{obs.type}' がマップ範囲外です！ y: {gy}"
            
        # 6. 壁装飾の配置検証（例: 魔法屋のシンボルの杖が正しい位置に配置され、テクスチャがロードされているか）
        expected_deco_id = "wall_decoration_masic_shop"
        deco_x, deco_y = 25, 27
        actual_deco_id = dungeon.wall_decoration_variants[deco_y][deco_x]
        assert actual_deco_id == expected_deco_id, f"座標({deco_x}, {deco_y})の装飾が期待値 '{expected_deco_id}' ではなく '{actual_deco_id}' です！"
        assert expected_deco_id in dungeon.textures, f"装飾 '{expected_deco_id}' のテクスチャがロードされていません！"
        print(f"  - OK: 壁装飾 '{expected_deco_id}' の配置・テクスチャロードを確認 (座標: {deco_x}, {deco_y})")
            
        print("[OK] 街のNPC＆障害物配置 自動テスト合格！")
        
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    test_village_spawning()
    pygame.quit()
