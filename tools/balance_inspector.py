
import os
import sys
import yaml

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from systems.data_loader import get_normalized_enemy_data, get_normalized_equipment_data, load_master_data, MASTER_DATA_DIR

def save_master_file(filename, data):
    """YAMLファイルを保存する"""
    path = os.path.join(MASTER_DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

def inspect_balance():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("====================================================")
        print("      ⚔️  Interactive Balance Editor ⚔️")
        print("====================================================")
        print(" [使い方]: 'ID パラメータ 値' で上書き")
        print("          敵例: slime hp 10 / 武器例: iron_sword attack_bonus 10")
        print(" [終了]: 'q' または 'exit' を入力\n")

        # 1. データのロード
        balance_cfg = load_master_data("balance.yml")
        player_base_atk = balance_cfg.get("PLAYER", {}).get("attack", 5)
        
        guild_data = load_master_data("guild.yml")
        from systems.data_loader import generate_rank_floor_map
        floor_map = generate_rank_floor_map(guild_data.get("GUILD_RANKS", []))
        
        enemies = get_normalized_enemy_data(floor_map)
        weapons, armor, shields, w_types = get_normalized_equipment_data(floor_map)
        
        rank_order = guild_data.get("RANK_ORDER", ["-", "F", "E", "D", "C", "B", "A", "S", "SS"])

        # 2. ランクごとに表示
        for rank in rank_order:
            if rank == "-": continue
            
            # そのランクの最強武器
            rank_weapons = [w for (wid, w) in weapons.items() if (w.get("min_rank") or w.get("rank")) == rank]
            if not rank_weapons:
                max_w_atk = 0
                best_w_name = "なし"
            else:
                best_w = max(rank_weapons, key=lambda x: x.get("attack_bonus", 0))
                max_w_atk = best_w.get("attack_bonus", 0)
                best_w_name = best_w.get("name", "Unknown")
            
            # 最終攻撃力 = プレイヤー基本 + 武器ボーナス
            final_atk = player_base_atk + max_w_atk
            
            # そのランクのモンスター
            rank_enemies = [e for (eid, e) in enemies.items() if (e.get("min_rank") or e.get("rank")) == rank and not e.get("is_static")]
            if not rank_enemies: continue

            print(f"--- ランク: {rank} (最強: {best_w_name} 最終ATK:{final_atk:.1f}) ---")
            print(f"  {'ID (内部名)':<16} | {'HP':>5} | {'DEF':>4} | {'Hits'} | {'Result'}")
            print(f"  {'-'*16}-+-{'-'*5}-+-{'-'*4}-+-{'-'*4}-+-------")
            
            for eid, e in enemies.items():
                if (e.get("min_rank") or e.get("rank")) != rank or e.get("is_static"): continue
                
                name = e.get("name", "Unknown")
                hp = e.get("hp", 10)
                defense = e.get("defense", 0)
                damage = max(1.0, final_atk - defense)
                
                import math
                hits = math.ceil(hp / damage)
                
                if hits <= 1: result = "✅ [1撃]"
                elif hits == 2: result = "⚔️ [2撃] 理想"
                elif hits == 3: result = "💀 [3撃] 手応え"
                else: result = f"‼️ [{hits}撃] 硬すぎ"
                
                print(f"  {eid:<16} | {hp:>5.1f} | {defense:>4.1f} | {hits:>4} | {result}")
            print("")

        # 3. 入力待ち
        cmd = input(">> ").strip()
        if cmd.lower() in ("q", "exit"):
            break
            
        parts = cmd.split()
        if len(parts) == 3:
            eid, param, val = parts[0], parts[1], parts[2]
            try:
                # 数値に変換
                val = float(val) if "." in val else int(val)
                
                # 生データのロード
                enemies_raw = load_master_data("enemies.yml")
                equip_raw = load_master_data("equipment.yml")
                
                found = False
                # 1. 敵データのチェック
                for section in ["ENEMY_DATA", "ENEMY_CATEGORIES"]:
                    if section in enemies_raw and eid in enemies_raw[section]:
                        enemies_raw[section][eid][param] = val
                        save_master_file("enemies.yml", enemies_raw)
                        print(f"\n[SUCCESS] 敵 {eid} の {param} を {val} に更新しました。")
                        found = True; break
                
                # 2. 装備データのチェック
                if not found:
                    for section in ["WEAPON_DATA", "ARMOR_DATA", "SHIELD_DATA", "WEAPON_CATEGORIES", "ARMOR_CATEGORIES"]:
                        if section in equip_raw and eid in equip_raw[section]:
                            equip_raw[section][eid][param] = val
                            save_master_file("equipment.yml", equip_raw)
                            print(f"\n[SUCCESS] 装備 {eid} の {param} を {val} に更新しました。")
                            found = True; break
                
                if not found:
                    print(f"\n[ERROR] ID '{eid}' が見つかりません。")
                
                import time; time.sleep(1)
            except Exception as e:
                print(f"\n[ERROR] {e}"); import time; time.sleep(2)
        else:
            print("\n[INFO] 'ID パラメータ 値' の形式で入力してください。")
            import time; time.sleep(1)

if __name__ == "__main__":
    inspect_balance()
