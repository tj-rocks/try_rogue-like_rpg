import os
import sys
import pygame
import random

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# [IMPORTANT] テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

from systems.dungeon import warp_to_floor
from components.sprites.player import Player
from components.sprites.enemy import Enemy
from constants import TILE_SIZE, ENEMY_DATA

def run_test():
    pygame.init()
    pygame.display.set_mode((1, 1))
    
    try:
        # 1. ボスリストの抽出 (50階以上は開発中のためスキップ)
        boss_list = [
            {"key": k, "floor": v.get("min_floor"), "name": v.get("name")}
            for k, v in ENEMY_DATA.items()
            if v.get("is_boss") and v.get("min_floor") is not None and v.get("min_floor") < 50
        ]
        
        print(f"[INFO] Testing {len(boss_list)} stable bosses: {[b['name'] for b in boss_list]}")

        # 2. 各ボスの確定出現テスト
        for boss_info in boss_list:
            test_boss_guaranteed_spawn(boss_info)
            test_boss_no_quest_spawn_rate(boss_info)
        
        # 3. 壁内スポーン防止テスト (全ボス階層対象)
        test_all_bosses_wall_prevention(boss_list)

        # 4. 【新規】全エンティティ（敵・アイテム・罠）の床乗り検証テスト
        test_all_entities_on_floor_tiles([1, 10, 20, 40])
        
        print("\n✅ All spawn validity tests PASSED!")
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        pygame.quit()

def test_boss_guaranteed_spawn(boss_info):
    """指定されたボスがその出現階層で確実に1体出現することを検証する"""
    b_key = boss_info["key"]
    b_floor = boss_info["floor"]
    b_name = boss_info["name"]
    
    print(f"\n--- {b_name} ({b_floor}F) 確定出現テスト開始 ---")
    player = Player()
    # 依頼受託状態にする（確定出現）
    player.active_quests.append({"target_key": b_key, "type": "hunt"})
    
    for i in range(5):
        dungeon = warp_to_floor(b_floor, player, spawn_reason="warped")
        bosses = [e for e in dungeon.enemies if e.type == b_key]
        if len(bosses) != 1:
            raise AssertionError(f"Floor {b_floor} should have exactly 1 {b_key}, but found {len(bosses)} (Iteration {i})")
    
    print(f"[OK] {b_name} spawned successfully in all attempts.")

def test_all_bosses_wall_prevention(boss_list):
    """ボスの占有グリッドが壁(0)にめり込んでいないかを検証する"""
    print("\n--- ボス占有エリア 壁内めり込み防止テスト開始 ---")
    player = Player()
    
    for boss_info in boss_list:
        b_floor = boss_info["floor"]
        b_name = boss_info["name"]
        b_key = boss_info["key"]
        print(f"Checking Floor {b_floor} ({b_name})...")
        
        # 討伐依頼を受託した状態にして確実に出現させる
        player.active_quests = [{"target_key": b_key, "type": "hunt"}]
        
        for i in range(3):
            dungeon = warp_to_floor(b_floor, player, spawn_reason="warped")
            for e in dungeon.enemies:
                occupied = e.get_occupied_grids(TILE_SIZE)
                for gx, gy in occupied:
                    if dungeon.map_data[gy][gx] == 0:
                        raise AssertionError(f"Entity {e.type} (size {e.width}x{e.height}) is overlapping with a wall at ({gx}, {gy}) on floor {b_floor}")
        print(f"[OK] Floor {b_floor} boss/enemy safety check passed.")

def test_boss_no_quest_spawn_rate(boss_info):
    """依頼を受託していない状態でのボス出現確率が約5%であることを検証する"""
    b_key = boss_info["key"]
    b_floor = boss_info["floor"]
    b_name = boss_info["name"]
    
    print(f"\n--- {b_name} ({b_floor}F) 依頼なし出現確率検証テスト開始 ---")
    player = Player()
    player.active_quests = [] # 依頼なし
    
    from constants import ENEMY_DATA
    import constants
    orig_chance = getattr(constants, "BOSS_NO_QUEST_SPAWN_CHANCE", 0.05)
    boss_chance = ENEMY_DATA.get(b_key, {}).get("spawn_chance")
    
    # 5%に固定してテストする
    constants.BOSS_NO_QUEST_SPAWN_CHANCE = 0.05
    if b_key in ENEMY_DATA:
        ENEMY_DATA[b_key]["spawn_chance"] = 0.05
        
    try:
        spawn_count = 0
        attempts = 40
        for i in range(attempts):
            dungeon = warp_to_floor(b_floor, player, spawn_reason="warped")
            bosses = [e for e in dungeon.enemies if e.type == b_key]
            if len(bosses) > 0:
                spawn_count += 1
                
        spawn_rate = spawn_count / attempts
        print(f"[INFO] {b_name} spawned {spawn_count} times out of {attempts} attempts ({spawn_rate * 100}%).")
        # 5%確率なので40回試行で0〜8回程度に収まるはず
        assert 0 <= spawn_count <= 8, f"Expected low spawn rate around 5%, but got {spawn_count}/{attempts}"
    finally:
        constants.BOSS_NO_QUEST_SPAWN_CHANCE = orig_chance
        if b_key in ENEMY_DATA:
            if boss_chance is None:
                ENEMY_DATA[b_key].pop("spawn_chance", None)
            else:
                ENEMY_DATA[b_key]["spawn_chance"] = boss_chance

def test_all_entities_on_floor_tiles(floors):
    """出現したすべての敵・アイテム・罠が、壁(0)ではなく床タイルの上に配置されているかを検証する"""
    print("\n--- 全エンティティ 床タイル配置検証テスト開始 ---")
    player = Player()
    
    for floor in floors:
        print(f"Verifying all entities on Floor {floor}...")
        dungeon = warp_to_floor(floor, player, spawn_reason="warped")
        
        # 1. 敵（障害物含む）の検証
        for e in dungeon.enemies:
            # 中心座標のグリッドを確認
            gx, gy = int((e.x + e.width/2) // TILE_SIZE), int((e.y + e.height/2) // TILE_SIZE)
            tile = dungeon.map_data[gy][gx]
            if tile == 0:
                raise AssertionError(f"Enemy {e.type} center is on a wall tile at ({gx}, {gy}) on floor {floor}")

        # 2. 落ちているアイテムの検証
        for item in dungeon.dropped_items:
            gx, gy = int(item.x // TILE_SIZE), int(item.y // TILE_SIZE)
            tile = dungeon.map_data[gy][gx]
            if tile == 0:
                raise AssertionError(f"Dropped item {getattr(item, 'item_key', 'unknown')} is on a wall tile at ({gx}, {gy}) on floor {floor}")

        # 3. 罠の検証
        for trap in dungeon.traps:
            # Trapクラスはx, yに「グリッド座標」を直接持っているため、そのまま使用する
            gx, gy = trap.x, trap.y
            tile = dungeon.map_data[gy][gx]
            if tile == 0:
                raise AssertionError(f"Trap {trap.type} is on a wall tile at ({gx}, {gy}) on floor {floor}")

        print(f"[OK] Floor {floor}: Verified {len(dungeon.enemies)} enemies, {len(dungeon.dropped_items)} items, and {len(dungeon.traps)} traps are on floor tiles.")

if __name__ == "__main__":
    run_test()
