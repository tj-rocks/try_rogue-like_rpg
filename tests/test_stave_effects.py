
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
    
    # [追加] 速度と移動フラグの検証 (スローモーションバグの防止)
    print(f"速度検証: 期待値 1200, 実際 {enemy.move_speed}")
    assert enemy.move_speed == 1200
    assert enemy.is_moving == True
    
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

def test_stave_bonuses():
    print("--- 魔法・杖装備ボーナステスト ---")
    player, dungeon, dialog = setup_test_environment()
    
    # モック装備を作成して魔法ボーナスを設定する
    mock_armor = MagicMock()
    mock_armor.get_stat.side_effect = lambda key, default=0: {
        "stave_heal_bonus": 10,
        "stave_invincible_bonus": 2,
        "stave_damage_bonus": 5,
        "stave_bonus": 3
    }.get(key, default)
    
    # プレイヤーの装備をモック化 (鎧のときだけ mock_armor を返し、盾のときは二重加算を防ぐため None を返す)
    player._find_equip_inst = MagicMock(side_effect=lambda inv, eid: mock_armor if inv == player.armor_inventory else None)
    player.equipped_armor = 1 # 装備中フラグ
    player.equipped_shield = None
    
    # 1. 杖回復ボーナス検証
    player.hp = 10
    player.max_hp = 200 # 回復限界キャップを避けるため最大HPを200にする
    stave_heal = StaveInstance("heal_stave", charges=5)
    # デフォルトの回復量は ratio 0.8 (200 * 0.8 = 160) 
    # ボーナス 10 が加算され、160 + 10 = 170 回復するはず (HP 10 -> 180)
    execute_stave(player, stave_heal, dungeon, dialog)
    print(f"回復ボーナス検証: 期待値 180, 実際 {player.hp}")
    assert player.hp == 180
    
    # 2. 杖無敵ターン延長ボーナス検証
    player.invincible_turns = 0
    stave_inv = StaveInstance("invincible_stave", charges=5)
    # デフォルトのターン数は 10
    # ボーナス 2 が加算され、10 + 2 = 12 ターン無敵になるはず
    execute_stave(player, stave_inv, dungeon, dialog)
    print(f"無敵ボーナス検証: 期待値 12, 実際 {player.invincible_turns}")
    assert player.invincible_turns == 12

    # 3. 杖取得時の回数ボーナス（stave_bonus）検証
    player.stave_inventory = []
    # デフォルト 5 回
    # ボーナス 3 が加算され、5 + 3 = 8 回になるはず
    player.add_stave_to_inventory("fire_stave", charges=5)
    added_stave = player.stave_inventory[0]
    print(f"杖回数ボーナス検証: 期待値 8, 実際 {added_stave.charges}")
    assert added_stave.charges == 8
    
    print("[OK] 魔法・杖装備ボーナステスト合格")

if __name__ == "__main__":
    try:
        test_light_stave()
        test_heal_stave()
        test_fire_stave()
        test_knockback_stave()
        test_invincible_stave()
        test_broken_stave()
        test_stave_bonuses()
        print("\n🎉 全ての杖効果テストに合格しました！")
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
