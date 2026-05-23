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
        
        drops = skeleton_info.get("drops", [])
        self.assertTrue(len(drops) >= 3, "テスト用の skeleton ドロップリストが正しくありません")
        
        # drops データの構築 (systems/entity_handler.py と同じロジック)
        drop_infos = []
        for drop in drops:
            item_key = drop.get("item")
            specific_rate = drop.get("rate")
            
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
            
            drop_infos.append({
                "item": item_key,
                "rarity": rarity,
                "rank_val": rarity,
                "rate": specific_rate
            })
            
        # 高レアリティ順（降順）にソート
        drop_infos.sort(key=lambda x: x["rank_val"], reverse=True)
        
        # 期待確率の計算
        # 高レアリティ順にソートされた順序で判定され、どれか1つドロップしたら終了するため、遮蔽効果を考慮する
        expected_rates = {}
        cumulative_not_dropped = 1.0
        
        for dinfo in drop_infos:
            item_key = dinfo["item"]
            base_rate = dinfo["rate"] if dinfo["rate"] is not None else ITEM_DROP_RATES.get(dinfo["rank_val"], 0.30)
            target_rate = base_rate * DROP_RATE_MULTIPLIER
            
            # このアイテムがドロップする期待確率
            item_expected_rate = cumulative_not_dropped * target_rate
            expected_rates[item_key] = item_expected_rate
            
            # 次のアイテムの判定に進む確率 (これまでがすべてドロップしなかった確率)
            cumulative_not_dropped *= (1.0 - target_rate)
            
        expected_rates[None] = cumulative_not_dropped
        
        print("\n--- Expected Drop Rates (Theoretical) ---")
        for k, v in expected_rates.items():
            print(f"  {k}: {v*100:.3f}%")
        print("------------------------------------------")
        
        # シミュレーション実行
        n_trials = 100000
        counts = {dinfo["item"]: 0 for dinfo in drop_infos}
        counts[None] = 0
        
        # 再現性のために乱数シードを固定
        random.seed(42)
        
        for _ in range(n_trials):
            dropped = False
            for dinfo in drop_infos:
                base_rate = dinfo["rate"] if dinfo["rate"] is not None else ITEM_DROP_RATES.get(dinfo["rank_val"], 0.30)
                target_rate = base_rate * DROP_RATE_MULTIPLIER
                
                if random.random() <= target_rate:
                    counts[dinfo["item"]] += 1
                    dropped = True
                    break
            if not dropped:
                counts[None] += 1
                
        # 結果表示とアサーション
        print("\n--- Simulated Drop Rates (100k Trials) ---")
        tolerances = {
            "old_sword": 0.005,      # 期待確率 2% に対し ±0.5% 誤差
            "broken_sword": 0.008,   # 期待確率 14.7% に対し ±0.8% 誤差
            "broken_armor": 0.008,   # 期待確率 12.5% に対し ±0.8% 誤差
            None: 0.010              # 期待確率 70.8% に対し ±1.0% 誤差
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
