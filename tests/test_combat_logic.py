
import pygame
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

from components.sprites.player import Player
from components.sprites.enemy import Enemy
from systems.dungeon import Dungeon
from systems.game_state import game_state

def test_combat_hit():
    pygame.init()
    # ヘッドレス環境を考慮
    screen = pygame.display.set_mode((800, 600))
    
    # 1. 初期化
    player = Player()
    player.x, player.y = 64, 64
    player.target_x, player.target_y = 64, 64
    player.facing = "down"
    player.attack = 500 # 確実にダメージが出るように
    
    # 2. ダンジョンと敵の配置
    dungeon = Dungeon(level=1, player=player)
    # 引数の順序修正: Enemy(x, y, enemy_type)
    enemy = Enemy(64, 128, "slime", player=player) 
    dungeon.enemies = [enemy]
    
    initial_hp = enemy.hp
    print(f"Testing Combat: Enemy Initial HP = {initial_hp}")
    
    hit_detected = False
    for i in range(20):
        print(f"Attack Trial {i+1}/20...")
        
        # 攻撃開始状態にする
        player.is_attacking = True
        from constants import ATTACK_ANIMATION_FRAMES
        player.attack_timer = ATTACK_ANIMATION_FRAMES
        
        # 判定フレームまで更新を回す
        # update_animationの中で _execute_strike が呼ばれるはず
        for _ in range(ATTACK_ANIMATION_FRAMES + 1):
            player.update_animation(dungeon, None)
            if enemy.hp < initial_hp:
                hit_detected = True
                break
        
        if hit_detected:
            print(f"[OK] Hit detected! Enemy HP: {initial_hp} -> {enemy.hp}")
            break
            
        # 次の試行のためにリセット
        player.is_attacking = False
        player.attack_timer = 0
        
    pygame.quit()
    
    if hit_detected:
        print("\n[RESULT] Combat Logic Test: PASSED")
        sys.exit(0)
    else:
        print("\n[RESULT] Combat Logic Test: FAILED (No hits in 20 trials)")
        sys.exit(1)

if __name__ == "__main__":
    test_combat_hit()
