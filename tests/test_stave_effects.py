
import os
import sys
import pygame
from unittest.mock import MagicMock, patch

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["TEST_MODE"] = "1"
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from components.sprites.enemy import Enemy
from systems.dungeon import Dungeon
from systems.magic_handler import execute_stave
from components.sprites.player import StaveInstance

def setup_test_environment():
    player = Player()
    player.name = "テスト勇者"
    dungeon = Dungeon(level=1, player=player)
    # テスト用にマップを床で埋める
    for y in range(dungeon.map_height):
        for x in range(dungeon.map_width):
            dungeon.map_data[y][x] = 1
    dialog = MagicMock()
    return player, dungeon, dialog

def test_light_stave():
    print("--- 燈の杖テスト ---")
    player, dungeon, dialog = setup_test_environment()
    dungeon.is_lighted = False
    
    stave = StaveInstance("light_stave", charges=5)
    execute_stave(player, stave, dungeon, dialog)
    
    assert stave.charges == 4
    assert dungeon.is_lighted == True
    # 全タイルが探索済みか
    for y in range(dungeon.map_height):
        for x in range(dungeon.map_width):
            assert dungeon.revealed_tiles[y][x] == True
    print("[OK] 燈の杖テスト合格")

def test_heal_stave():
    print("--- 回復の杖テスト ---")
    player, dungeon, dialog = setup_test_environment()
    player.hp = 10
    
    stave = StaveInstance("heal_stave", charges=5)
    execute_stave(player, stave, dungeon, dialog)
    
    assert stave.charges == 4
    assert player.hp > 10
    print("[OK] 回復の杖テスト合格")

def test_fire_stave():
    print("--- 火炎の杖テスト ---")
    player, dungeon, dialog = setup_test_environment()
    # 座標を明示的に固定 (グリッド 2, 2)
    ts = dungeon.tile_size
    player.x = 2 * ts
    player.y = 2 * ts
    player.facing = "right"
    
    # プレイヤーの正面(右) グリッド (3, 2) に敵を配置
    enemy = Enemy(3 * ts, 2 * ts, "slime")
    enemy.hp = 100
    dungeon.enemies = [enemy]
    
    stave = StaveInstance("fire_stave", charges=5)
    execute_stave(player, stave, dungeon, dialog)
    
    assert stave.charges == 4
    # ダメージが当たってHPが減っているか検証
    print(f"敵HP検証: 期待値 < 100, 実際 {enemy.hp}")
    assert enemy.hp < 100
    print("[OK] 火炎の杖テスト合格")

def test_knockback_stave():
    print("--- 吹き飛ばしの杖テスト ---")
    player, dungeon, dialog = setup_test_environment()
    ts = dungeon.tile_size
    player.x = 2 * ts
    player.y = 2 * ts
    player.facing = "right"
    
    # 目の前 (3, 2) に敵を配置
    enemy = Enemy(3 * ts, 2 * ts, "slime")
    enemy.target_x = enemy.x
    enemy.target_y = enemy.y
    dungeon.enemies = [enemy]
    
    stave = StaveInstance("knockback_stave", charges=5)
    execute_stave(player, stave, dungeon, dialog)
    
    assert stave.charges == 4
    # 座標が右に移動しているか (target_x が 3*ts より大きくなっているはず)
    print(f"位置検証: 期待値 > {3 * ts}, 実際 {enemy.target_x}")
    assert enemy.target_x > 3 * ts
    print("[OK] 吹き飛ばしの杖テスト合格")

def test_invincible_stave():
    print("--- 無敵の杖テスト ---")
    player, dungeon, dialog = setup_test_environment()
    player.invincible_turns = 0
    
    stave = StaveInstance("invincible_stave", charges=5)
    execute_stave(player, stave, dungeon, dialog)
    
    assert stave.charges == 4
    assert player.invincible_turns > 0
    print("[OK] 無敵の杖テスト合格")

def test_broken_stave():
    print("--- 壊れた杖テスト ---")
    player, dungeon, dialog = setup_test_environment()
    
    # 壊れた杖は初期回数0
    stave = StaveInstance("broken_stave", charges=0)
    msg = execute_stave(player, stave, dungeon, dialog)
    
    assert "回数が足りない" in msg
    assert stave.charges == 0
    print("[OK] 壊れた杖テスト合格")

if __name__ == "__main__":
    try:
        test_light_stave()
        test_heal_stave()
        test_fire_stave()
        test_knockback_stave()
        test_invincible_stave()
        test_broken_stave()
        print("\n🎉 全ての杖効果テストに合格しました！")
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
