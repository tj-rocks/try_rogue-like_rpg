import os
import sys
import pygame
import random
from unittest.mock import MagicMock, patch, PropertyMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化（ヘッドレスモード）
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from components.sprites.enemy import Enemy
from systems.combat_handler import calculate_damage

def test_evasion_statistical():
    print("\n[TEST] 回避率の統計テストを開始 (1000回試行)...")
    
    # 1. 回避率 20% のテスト
    player = Player()
    # プロパティをモックして回避率を 20 に固定
    with patch.object(Player, 'eva_bonus', new_callable=PropertyMock) as mock_eva:
        mock_eva.return_value = 20
        with patch.object(Player, 'block_chance_close', new_callable=PropertyMock) as mock_block:
            mock_block.return_value = 0.0
            
            enemy = Enemy(0, 0, "slime")
            enemy.accuracy_close = 100 # 必中
            enemy.facing = "right" # playerを向く
            player.x, player.y = 64, 0
            player.facing = "left" # enemyを向く (正面判定)
            
            miss_count = 0
            trials = 1000
            
            for _ in range(trials):
                dmg, is_crit, is_miss = calculate_damage(enemy, player)
                if is_miss:
                    miss_count += 1
            
            miss_rate = miss_count / trials
            print(f"回避率 20% テスト結果: Miss={miss_count}/{trials} ({miss_rate*100:.1f}%)")
            
            # 統計的な誤差を考慮 (15% ~ 25% なら合格)
            assert 0.15 <= miss_rate <= 0.25, f"回避率が異常です: {miss_rate*100:.1f}% (Target: 20%)"

    # 2. 回避率 20% + ブロック率 10% のテスト
    with patch.object(Player, 'eva_bonus', new_callable=PropertyMock) as mock_eva:
        mock_eva.return_value = 20
        with patch.object(Player, 'block_chance_close', new_callable=PropertyMock) as mock_block:
            mock_block.return_value = 0.1 # 10%
            
            miss_count = 0
            for _ in range(trials):
                dmg, is_crit, is_miss = calculate_damage(enemy, player)
                if is_miss:
                    miss_count += 1
            
            combined_rate = miss_count / trials
            print(f"回避 20% + ブロック 10% テスト結果: Miss={miss_count}/{trials} ({combined_rate*100:.1f}%)")
            
            # 統計的な誤差を考慮 (25% ~ 35% なら合格)
            assert 0.25 <= combined_rate <= 0.35, f"回避+ブロック率が異常です: {combined_rate*100:.1f}% (Target: 30%)"

    print("[SUCCESS] 回避率・ブロック率の統計テストが正常に完了しました。")

if __name__ == "__main__":
    try:
        test_evasion_statistical()
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
