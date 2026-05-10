import os
import sys
import pygame
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化（ヘッドレスモード）
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()

from systems.combat_handler import deal_damage

def test_decimal_attack_impact():
    print("--- [検証] 小数点攻撃力の有効性テスト ---")
    
    # モックの作成
    player = MagicMock()
    enemy = MagicMock()
    
    # 共通設定
    player.name = "Player"
    player.x, player.y = 64, 64
    player.facing = "down"
    
    enemy.name = "Slime"
    enemy.is_god = False
    enemy.invincible_turns = 0
    enemy.total_defense = 7.0
    enemy.hp = 100
    enemy.is_dead = False
    enemy.x, enemy.y = 64, 128
    enemy.facing = "down"
    player.x, player.y = 64, 64
    player.facing = "down"
    player.crit_rate = 0 # クリティカル排除
    player.crit_bonus = 0
    player.status_to_inflict = None
    player.status_chance = 0
    player.weapon = None
    
    # ---------------------------------------------------------
    # ケースA: 攻撃力 8.0 (1.0 -> 1ダメージ)
    # ---------------------------------------------------------
    player.total_attack = 8.0
    
    damages_a = []
    for _ in range(10):
        msg, dmg, _, _ = deal_damage(player, enemy, is_magic=True) # 必中
        damages_a.append(dmg)
    
    avg_a = sum(damages_a) / len(damages_a)
    print(f"攻撃力 {player.total_attack} の時のダメージ平均: {avg_a:.2f} (Min: {min(damages_a)}, Max: {max(damages_a)})")
    
    # ---------------------------------------------------------
    # ケースB: 攻撃力 8.2 (1.2 -> 切り上げで2ダメージ)
    # ---------------------------------------------------------
    player.total_attack = 8.2
    
    damages_b = []
    for _ in range(10):
        msg, dmg, _, _ = deal_damage(player, enemy, is_magic=True)
        damages_b.append(dmg)
        
    avg_b = sum(damages_b) / len(damages_b)
    print(f"攻撃力 {player.total_attack} の時のダメージ平均: {avg_b:.2f} (Min: {min(damages_b)}, Max: {max(damages_b)})")

    if avg_b > avg_a:
        print("[OK] 小数点以下の攻撃力がダメージ計算に正しく反映されています。")
    else:
        print("[NG] 小数点以下の攻撃力が無視されています。")

if __name__ == "__main__":
    test_decimal_attack_impact()
