
import os
import sys
import pygame
import random

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化（ヘッドレスモード）
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
screen = pygame.display.set_mode((800, 600))

from systems.session_handler import init_ui_elements, start_new_game
from systems.game_state import game_state
from systems.scene_handler import handle_game
from components.sprites.enemy import Enemy
from constants import (
    KEY_ATTACK, ENEMY_DATA, ATTACK_ANIMATION_FRAMES
)

def test_actual_combat_interaction():
    print("--- 敵との実戦交戦シミュレーションテスト開始 ---")
    
    try:
        # 1. 初期化
        ui_elements = init_ui_elements(800, 600)
        player, dungeon = start_new_game(ui_elements, game_state)
        
        # 2. プレイヤーの目の前（右隣）に敵をスポーンさせる
        # 村（Floor 0）の空いている場所に移動してから配置
        player.x = 10 * dungeon.tile_size
        player.y = 10 * dungeon.tile_size
        player.target_x = player.x
        player.target_y = player.y
        player.facing = "right"
        
        enemy_x = player.x + dungeon.tile_size
        enemy_y = player.y
        test_enemy_type = "slime" # 定番のスライム
        enemy = Enemy(enemy_x, enemy_y, test_enemy_type)
        dungeon.current_floor = 1
        player.current_floor = 1
        enemy.current_floor = 1
        dungeon.enemies.append(enemy)
        
        initial_enemy_hp = enemy.hp
        initial_player_hp = player.hp
        print(f"戦闘開始: プレイヤーHP={initial_player_hp}, 敵({test_enemy_type})HP={initial_enemy_hp}")

        # 3. プレイヤーの攻撃実行
        print("[Step 1] プレイヤーの攻撃（Spaceキー入力）")
        events = [pygame.event.Event(pygame.KEYDOWN, {"key": KEY_ATTACK})]
        
        # 攻撃アニメーションが終わるまでループを回す
        attack_triggered = False
        damage_dealt = False
        
        for frame in range(100):
            # ゲーム処理
            dungeon = handle_game(screen, events, player, dungeon, ui_elements, game_state)
            events = [] # イベントは1回だけ送る
            
            if player.is_attacking:
                attack_triggered = True
            
            if enemy.damage_flash_timer > 0 and not damage_dealt:
                print(f"[Frame {frame}] 敵の被ダメージを検知！ HP: {enemy.hp}")
                damage_dealt = True
                
            # 敵の攻撃開始チェック
            if enemy.is_attacking:
                print(f"[Frame {frame}] 敵の反撃（突進攻撃）を検知！")
            
            # プレイヤーがダメージを受けたかチェック
            if player.hp < initial_player_hp:
                print(f"[Frame {frame}] プレイヤーの被ダメージを検知！ HP: {player.hp}")
                break

            # 一定時間経過して何も起きなければ失敗
            if frame > 80 and not attack_triggered:
                raise Exception("プレイヤーの攻撃がトリガーされませんでした")

        # 4. 最終検証
        assert attack_triggered, "プレイヤーが攻撃状態になりませんでした"
        assert damage_dealt, "敵にダメージが通りませんでした"
        
        print("[OK] 交戦シミュレーションテスト合格！")
        
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    try:
        test_actual_combat_interaction()
        pygame.quit()
    except Exception as e:
        sys.exit(1)
