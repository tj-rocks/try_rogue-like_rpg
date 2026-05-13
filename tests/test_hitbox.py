
import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

# Pygameの初期化
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from components.sprites.enemy import Enemy
from components.sprites.weapon import OneHanded, Spear
from constants import TILE_SIZE

class MockDungeon:
    def __init__(self):
        self.tile_size = TILE_SIZE
        self.enemies = []
        self.traps = []
        self.map_width = 100
        self.map_height = 100
        self.map_data = [[1 for _ in range(100)] for _ in range(100)]
    
    def _get_wall_texture_key(self, x, y):
        return "wall_top"

def test_hitbox_logic():
    print("--- 判定ロジックテスト開始 ---")
    
    dungeon = MockDungeon()
    player = Player()
    
    # 1. 武器攻撃範囲の検証（片手剣：正面1マス）
    weapon_sword = OneHanded({"name": "テスト剣", "type": "OneHanded"})
    gx, gy = 5, 5
    player.x, player.y = gx * TILE_SIZE, gy * TILE_SIZE
    
    player.facing = "up"
    hits = weapon_sword.get_hit_grids(player.facing, gx, gy, dungeon)
    print(f"片手剣 (UP) 攻撃範囲: {hits}")
    assert (5, 4) in hits, "片手剣(UP)は(5, 4)を攻撃すべきです"
    
    player.facing = "right"
    hits = weapon_sword.get_hit_grids(player.facing, gx, gy, dungeon)
    print(f"片手剣 (RIGHT) 攻撃範囲: {hits}")
    assert (6, 5) in hits, "片手剣(RIGHT)は(6, 5)を攻撃すべきです"

    # 2. 槍の検証（正面2マス）
    weapon_spear = Spear({"name": "テスト槍", "type": "Spear"})
    player.facing = "up"
    hits = weapon_spear.get_hit_grids(player.facing, gx, gy, dungeon)
    print(f"槍 (UP) 攻撃範囲: {hits}")
    assert (5, 4) in hits and (5, 3) in hits, "槍(UP)は(5, 4)と(5, 3)を攻撃すべきです"

    # 3. 巨大な敵への当たり判定検証
    # スイスイスライム相当(2x2)を (6, 4) を左上として配置。
    # プレイヤー (5, 5) から上(5, 4)を攻撃した際に、(6, 4) にいる巨大敵に当たるか？
    # 巨大敵が(6, 4)配置で幅2なら、(6, 4), (7, 4), (6, 5), (7, 5) を占有する。
    # あれ、これだと (5, 4) には当たらないな。
    
    # 配置を変更：(5.5, 4.5) に配置（ピクセル単位で重なっている状態）
    # 5.5 * 64 = 352.  4.5 * 64 = 288.
    # 幅 128 (2タイル分)
    huge_enemy = Enemy(352, 288, "suisui_slime")
    huge_enemy.width = TILE_SIZE * 2
    huge_enemy.height = TILE_SIZE * 2
    
    occupied = huge_enemy.get_occupied_grids(TILE_SIZE)
    print(f"巨大敵 (352, 288) 占有マス: {occupied}")
    # (352, 288) から 128x128
    # X: 352/64=5.5, (352+127)/64=7.48 -> 5, 6, 7
    # Y: 288/64=4.5, (288+127)/64=6.48 -> 4, 5, 6
    
    # プレイヤーが (5, 5) から上を攻撃 (5, 4)
    player.facing = "up"
    player.weapon = weapon_sword
    hit_grids = player.weapon.get_hit_grids(player.facing, 5, 5, dungeon)
    
    hit_detected = False
    for hgx, hgy in hit_grids:
        if (hgx, hgy) in occupied:
            hit_detected = True
            print(f"[OK] 巨大敵の占有マス ({hgx}, {hgy}) にヒットしました")
            
    assert hit_detected, "巨大敵への当たり判定が機能していません"

    print("--- すべての判定テストに合格しました！ ---")

if __name__ == "__main__":
    try:
        test_hitbox_logic()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
