import sys
import os
import random
import unittest

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

from constants import (
    ENEMY_DATA,
    ITEM_DROP_RATES,
    DROP_RATE_MULTIPLIER,
    WEAPON_DATA,
    ARMOR_DATA,
    SHIELD_DATA,
    CONSUMABLE_DATA,
    STAVE_DATA
)

class TestEnemyDropRates(unittest.TestCase):
    def test_skeleton_drop_rates_simulation(self):
        """100,000回シミュレーションを行い、スケルトンのドロップ確率が期待値に収まるか検証する"""
        skeleton_info = ENEMY_DATA.get("skeleton")
        self.assertIsNotNone(skeleton_info, "skeleton のデータが ENEMY_DATA に存在しません")
        
        drops = skeleton_info.get("drops", {})
        self.assertIsInstance(drops, dict, "skeleton の drops は dict 構造である必要があります")
        
        normal_items = drops.get("normal", [])
        rare_items = drops.get("rare", [])
        
        normal_drop_rate = skeleton_info.get("normal_drop_rate", 0.1)
        rare_drop_rate = skeleton_info.get("rare_drop_rate", 0.01)
        
        target_normal_rate = normal_drop_rate * DROP_RATE_MULTIPLIER
        target_rare_rate = rare_drop_rate * DROP_RATE_MULTIPLIER
        
        # 各種アイテムの重み計算ヘルパー
        def get_item_rarity(item_key):
            rarity = 1
            if item_key in WEAPON_DATA:
                rarity = WEAPON_DATA[item_key].get("rarity", 1)
            elif item_key in ARMOR_DATA:
                rarity = ARMOR_DATA[item_key].get("rarity", 1)
            elif item_key in SHIELD_DATA:
                rarity = SHIELD_DATA[item_key].get("rarity", 1)
            elif item_key in CONSUMABLE_DATA:
                rarity = CONSUMABLE_DATA[item_key].get("rarity", 1)
            elif item_key in STAVE_DATA:
                rarity = STAVE_DATA[item_key].get("rarity", 1)
            return rarity

        # レア枠の重み
        rare_weights = []
        for item in rare_items:
            r = get_item_rarity(item)
            rare_weights.append(ITEM_DROP_RATES.get(r, 0.1))
        sum_rare_weights = sum(rare_weights) if rare_weights else 1.0
        
        # 通常枠の重み
        normal_weights = []
        for item in normal_items:
            r = get_item_rarity(item)
            normal_weights.append(ITEM_DROP_RATES.get(r, 0.1))
        sum_normal_weights = sum(normal_weights) if normal_weights else 1.0
        
        # 期待確率の計算
        expected_rates = {}
        
        # レア枠の期待値
        for item, w in zip(rare_items, rare_weights):
            # レア判定に当選し、かつそのアイテムが選ばれる確率
            expected_rates[item] = target_rare_rate * (w / sum_rare_weights)
            
        # 通常枠の期待値
        for item, w in zip(normal_items, normal_weights):
            # レア判定に落選し、かつ通常判定に当選し、そのアイテムが選ばれる確率
            expected_rates[item] = (1.0 - target_rare_rate) * target_normal_rate * (w / sum_normal_weights)
            
        # 何もドロップしない期待値
        expected_rates[None] = (1.0 - target_rare_rate) * (1.0 - target_normal_rate)
        
        print("\n--- Expected Drop Rates (Theoretical) ---")
        for k, v in expected_rates.items():
            print(f"  {k}: {v*100:.3f}%")
        print("------------------------------------------")
        
        # シミュレーション実行
        n_trials = 100000
        counts = {item: 0 for item in normal_items + rare_items}
        counts[None] = 0
        
        # 再現性のために乱数シードを固定
        random.seed(42)
        
        for _ in range(n_trials):
            dropped = False
            # 1. レアドロップ判定
            if random.random() <= target_rare_rate:
                if rare_items:
                    chosen = random.choices(rare_items, weights=rare_weights, k=1)[0]
                    counts[chosen] += 1
                    dropped = True
            
            # 2. 通常ドロップ判定 (レアドロップしなかった場合)
            if not dropped:
                if random.random() <= target_normal_rate:
                    if normal_items:
                        chosen = random.choices(normal_items, weights=normal_weights, k=1)[0]
                        counts[chosen] += 1
                        dropped = True
                        
            if not dropped:
                counts[None] += 1
                
        # 結果表示とアサーション
        print("\n--- Simulated Drop Rates (100k Trials) ---")
        
        # 誤差許容値 (設定値に合わせたスケール)
        tolerances = {
            "old_sword": 0.005,      # 期待確率 ~1.2% に対し ±0.5% 誤差
            "iron_sword": 0.005,     # 期待確率 ~1.8% に対し ±0.5% 誤差
            "broken_sword": 0.008,   # 期待確率 ~7.3% に対し ±0.8% 誤差
            "broken_armor": 0.008,   # 期待確率 ~7.3% に対し ±0.8% 誤差
            None: 0.010              # 期待確率 ~82.4% に対し ±1.0% 誤差
        }
        
        for k, count in counts.items():
            sim_rate = count / n_trials
            exp_rate = expected_rates[k]
            diff = abs(sim_rate - exp_rate)
            print(f"  {k}: {sim_rate*100:.3f}% (Diff: {diff*100:.3f}%)")
            
            # 各アイテムの誤差範囲内に収まっているかをアサート
            tolerance = tolerances.get(k, 0.01)
            self.assertLessEqual(diff, tolerance, f"{k} のドロップ確率の誤差が許容値({tolerance*100}%)を超えています: {diff*100:.3f}%")
        print("------------------------------------------")

if __name__ == "__main__":
    unittest.main()
