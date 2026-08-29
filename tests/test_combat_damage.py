import os
import sys
import pygame
from unittest.mock import MagicMock, patch

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

# Pygameの初期化（ヘッドレスモード）
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from components.sprites.enemy import Enemy
from systems.combat_handler import calculate_damage, deal_damage


def test_player_miss_message_omits_self_name():
    player = Player()
    enemy = Enemy(0, 0, "slime")

    with patch("systems.combat_handler.calculate_damage", return_value=(0, False, True)):
        message, _, _, _ = deal_damage(player, enemy)

    assert message == "ミス 攻撃は 外れた"
    assert "自分" not in message


def test_player_damage_message_omits_self_name():
    player = Player()
    enemy = Enemy(0, 0, "slime")

    with patch("systems.combat_handler.calculate_damage", return_value=(10, False, False)):
        message, damage, _, _ = deal_damage(player, enemy)

    assert message == f"{enemy.name} に 10 ダメージを与えた"
    assert damage == 10
    assert "自分" not in message


def test_damage_to_player_message_omits_self_name():
    player = Player()
    enemy = Enemy(0, 0, "slime")

    with patch("systems.combat_handler.calculate_damage", return_value=(10, False, False)):
        message, damage, _, _ = deal_damage(enemy, player)

    assert message == f"{enemy.name} は 10 ダメージを与えた"
    assert damage == 10
    assert "自分" not in message

def test_combat_damage_calculation():
    print("\n[TEST] 戦闘ダメージ計算テストを開始 (実クラス使用版)...")

    # --- 1. プレイヤー攻撃のテスト (正面攻撃) ---
    # 攻撃力 8, 敵防御 1 -> 新式ベースダメージ: 8 * (50 / 51) = 7.84 -> 繰り上げで 8.0
    player = Player()
    player.attack = 8
    player.x, player.y = 64, 0
    player.facing = "left"
    player.unequip_armor()
    player.unequip_weapon()
    
    enemy = Enemy(0, 0, "slime")
    enemy.defense = 1
    enemy.facing = "right"
    
    # 乱数制御: 1回目(Miss判定)は0.0, 2回目(Crit判定)は1.0. random.uniformは0.1(中央値)を返すよう固定
    with patch('random.random', side_effect=[0.0, 1.0]):
        with patch('random.uniform', return_value=0.1):
            print(f"DEBUG: AttackerAtk={player.total_attack}, TargetDef={getattr(enemy, 'total_defense', enemy.defense)}")
            dmg, is_crit, is_miss = calculate_damage(player, enemy)
            print(f"プレイヤー攻撃テスト(正面): Damage={dmg}, Crit={is_crit}, Miss={is_miss}")
            assert dmg == 8.0, f"ダメージ計算が異常です: {dmg} (Expected: 8.0)"

    # --- 2. 敵攻撃のテスト (装備なし) ---
    # 敵攻撃 12, プレイヤー防御 3 -> 新式ベースダメージ: 12 * (50 / 53) = 11.32 -> 繰り上げで 12.0
    enemy_atk = Enemy(0, 0, "mawaru_kame")
    enemy_atk.attack = 12
    enemy_atk.facing = "left"
    
    player_def = Player()
    player_def.defense = 3
    player_def.x, player_def.y = 0, 0
    player_def.facing = "right"
    player_def.unequip_armor()
    
    with patch('random.random', side_effect=[0.0, 1.0]):
        with patch('random.uniform', return_value=0.1):
            dmg, is_crit, is_miss = calculate_damage(enemy_atk, player_def)
            print(f"敵攻撃テスト(装備なし): Damage={dmg}, Def={player_def.total_defense}")
            assert player_def.total_defense == 3
            assert dmg == 12.0, f"ダメージ計算が異常です: {dmg} (Expected: 12.0)"

    # --- 3. 敵攻撃のテスト (防具装備時 - 二重加算バグの修正確認) ---
    # 敵攻撃 23, プレイヤー防御 13 (3 + レザー10) -> 新式ベースダメージ: 23 * (50 / 63) = 18.25 -> 繰り上げで 19.0
    player_equipped = Player()
    player_equipped.defense = 3
    player_equipped.x, player_equipped.y = 0, 0
    player_equipped.facing = "right"
    
    # レザー胸当てを装備
    from components.sprites.player import EquipInstance
    armor = EquipInstance("armor", "leather_breastplate")
    player_equipped.armor_inventory.append(armor)
    player_equipped.change_armor(armor.iid)
    
    print(f"防具装備状態: BaseDef={player_equipped.defense}, TotalDef={player_equipped.total_defense}")
    assert player_equipped.total_defense == 13, f"防御力が異常です(二重加算の疑い): {player_equipped.total_defense}"

    enemy_strong = Enemy(64, 0, "mawaru_kame")
    enemy_strong.attack = 23
    enemy_strong.facing = "left"
    
    with patch('random.random', side_effect=[0.0, 1.0]):
        with patch('random.uniform', return_value=0.1):
            dmg, is_crit, is_miss = calculate_damage(enemy_strong, player_equipped)
            print(f"敵攻撃テスト(防具あり): Damage={dmg}, TotalDef={player_equipped.total_defense}")
            assert dmg == 19.0, f"ダメージ計算が異常です: {dmg} (Expected: 19.0)"

    print("[SUCCESS] ダメージ計算テストが正常に完了しました。")

if __name__ == "__main__":
    try:
        test_combat_damage_calculation()
        print("\nALL COMBAT DAMAGE TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
