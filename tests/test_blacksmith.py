
import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["TEST_MODE"] = "1"
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player, EquipInstance
from constants import WEAPON_DATA, ARMOR_DATA

def test_enhancement_stats():
    print("--- 鍛冶・強化ステータステスト開始 ---")
    
    player = Player()
    
    # 1. 武器の強化テスト
    weapon_key = "iron_sword"
    if weapon_key not in WEAPON_DATA:
        print(f"[SKIP] {weapon_key} がデータにありません")
        return
        
    # 初期状態
    inst_w = EquipInstance("weapon", weapon_key)
    player.weapon_inventory = [inst_w]
    player.equipped_weapon = inst_w.iid
    
    atk_base = player.total_attack
    print(f"武器初期状態: {inst_w.get_name()}, 総攻撃力: {atk_base}")
    
    # 強化実行 (攻撃力を+10回): 新方式は per-stat の stats を埋める必要がある
    inst_w.apply_upgrade("attack_bonus", 10)
    atk_plus_10 = player.total_attack
    print(f"武器強化後 (+10): {inst_w.get_name()}, 総攻撃力: {atk_plus_10}")
    
    assert atk_plus_10 > atk_base, "強化後に攻撃力が上昇していません"
    
    # 2. 防具の強化テスト
    armor_key = "leather_breastplate"
    if armor_key not in ARMOR_DATA:
        print(f"[SKIP] {armor_key} がデータにありません")
    else:
        inst_a = EquipInstance("armor", armor_key)
        player.armor_inventory = [inst_a]
        player.change_armor(inst_a.iid)
        
        def_base = player.total_defense
        print(f"防具初期状態: {inst_a.get_name()}, 総防御力: {def_base}")
        
        # 強化実行 (防御力を+10回)
        inst_a.apply_upgrade("defense_bonus", 10)
        player.update_equipment_stats() # ステータス再計算をトリガー
        def_plus_10 = player.total_defense
        print(f"防具強化後 (+10): {inst_a.get_name()}, 総防御力: {def_plus_10}")
        
        assert def_plus_10 > def_base, "強化後に防御力が上昇していません"

    # 3. 強化限界（growth設定）の検証
    # growth パラメータがある場合、特定の回数以降は上昇が鈍化するはず
    data = WEAPON_DATA[weapon_key]
    growth = data.get("growth")
    if growth:
        times_limit = growth.get("times_limit", 50)
        print(f"強化限界設定を発見: times_limit={times_limit}")
        
        # 新方式: per-stat の強化回数(stats)でボーナスが決まる
        inst_w.stats["attack_bonus"] = times_limit
        atk_at_limit = player.total_attack
        
        inst_w.stats["attack_bonus"] = times_limit + 1
        atk_over_limit = player.total_attack
        
        diff = atk_over_limit - atk_at_limit
        print(f"限界突破時の上昇量: {diff}")
        # 限界近傍では上昇が鈕化する設計（減衰カーブ）
    
    print("[OK] 鍛冶・強化ステータステスト合格！")

if __name__ == "__main__":
    try:
        test_enhancement_stats()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
