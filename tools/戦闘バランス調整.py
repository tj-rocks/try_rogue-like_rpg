
import http.server
import socketserver
import json
import os
import sys
import yaml
from urllib.parse import urlparse, parse_qs

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from systems.data_loader import get_normalized_enemy_data, get_normalized_equipment_data, load_master_data, MASTER_DATA_DIR, generate_rank_floor_map

PORT = 5001
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/' or self.path == '/dashboard.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            ui_path = os.path.join(DIRECTORY, 'dashboard.html')
            with open(ui_path, 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # 全データをロードして返す
            print("[API] Loading master data...")
            balance_cfg = load_master_data("balance.yml")
            guild_data = load_master_data("guild.yml")
            
            ranks_list = guild_data.get("GUILD_RANKS", [])
            print(f"[API] Found {len(ranks_list)} ranks")
            
            from systems.data_loader import generate_rank_floor_map
            floor_map = generate_rank_floor_map(ranks_list)
            
            enemies = get_normalized_enemy_data(floor_map)
            weapons, armor, shields, w_cats, a_cats, s_cats = get_normalized_equipment_data(floor_map)
            
            print(f"[API] Normalized {len(enemies)} enemies, {len(weapons)} weapons, {len(armor)} armors")
            
            data = {
                "balance": balance_cfg,
                "guild": guild_data,
                "enemies": enemies,
                "weapons": weapons,
                "armor": armor,
                "shields": shields,
                "raw_enemies": load_master_data("enemies.yml"),
                "raw_equipment": {
                    **load_master_data("weapons.yml"),
                    **load_master_data("armors.yml"),
                    **load_master_data("shields.yml")
                }
            }
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        else:
            # 静的ファイルを返す
            if self.path == '/':
                self.path = '/dashboard.html'
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/update':
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length).decode('utf-8'))
            
            file_type = post_data.get("file") # "enemies" or "equipment"
            target_id = post_data.get("id")
            param = post_data.get("param")
            value = post_data.get("value")
            
            KEY_MAP_TO_NEW = {
                "attack_bonus": "attack",
                "defense_bonus": "defense",
                "hp_bonus": "hp",
                "evasion_bonus": "eva",
                "accuracy_bonus_close": "accuracy_close",
                "accuracy_bonus_ranged": "accuracy_range",
                "block_chance_close": "block_chance_close",
                "block_chance_ranged": "block_chance_ranged",
            }
            
            if file_type == "equipment":
                weapons_raw = load_master_data("weapons.yml")
                armors_raw = load_master_data("armors.yml")
                shields_raw = load_master_data("shields.yml")
                
                if "WEAPON_DATA" in weapons_raw and target_id in weapons_raw["WEAPON_DATA"]:
                    filename = "weapons.yml"
                elif "WEAPON_CATEGORIES" in weapons_raw and target_id in weapons_raw["WEAPON_CATEGORIES"]:
                    filename = "weapons.yml"
                elif "ARMOR_DATA" in armors_raw and target_id in armors_raw["ARMOR_DATA"]:
                    filename = "armors.yml"
                elif "ARMOR_CATEGORIES" in armors_raw and target_id in armors_raw["ARMOR_CATEGORIES"]:
                    filename = "armors.yml"
                elif "SHIELD_DATA" in shields_raw and target_id in shields_raw["SHIELD_DATA"]:
                    filename = "shields.yml"
                elif "SHIELD_CATEGORIES" in shields_raw and target_id in shields_raw["SHIELD_CATEGORIES"]:
                    filename = "shields.yml"
                else:
                    filename = "equipment.yml"
            else:
                filename = f"{file_type}.yml"
                
            raw_data = load_master_data(filename)
            
            # 数値変換
            try:
                if isinstance(value, str) and "." in value:
                    value = float(value)
                elif isinstance(value, str):
                    value = int(value)
            except:
                pass
            
            # サージカル・アップデート（行単位での置換）の試行
            path = os.path.join(MASTER_DATA_DIR, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                updated = False
                in_data_section = False
                in_target_block = False
                if filename == "enemies.yml":
                    section_key = "ENEMY_DATA:"
                elif filename == "weapons.yml":
                    section_key = "WEAPON_DATA:"
                elif filename == "armors.yml":
                    section_key = "ARMOR_DATA:"
                elif filename == "shields.yml":
                    section_key = "SHIELD_DATA:"
                else:
                    section_key = None
                
                new_key = KEY_MAP_TO_NEW.get(param, param) if file_type == "equipment" else param
                
                new_lines = []
                for line in lines:
                    stripped = line.strip()
                    
                    # セクションの開始を確認
                    if section_key and stripped.startswith(section_key):
                        in_data_section = True
                    elif in_data_section and stripped.endswith(":") and not line.startswith(" "):
                        # 次のトップレベルキーが来たらセクション終了（簡易判定）
                        if not stripped.startswith(("#", section_key.split(":")[0])):
                             in_data_section = False
                    
                    # ターゲット（個体）のブロックを確認
                    if in_data_section and stripped == f"{target_id}:":
                        in_target_block = True
                        param_found = False
                    elif in_target_block and stripped.endswith(":") and line.startswith("  ") and not line.startswith("    "):
                        # 次の個体ブロックが来たら、またはセクションが終わったら
                        if stripped != f"{target_id}:":
                            # パラメータが見つからなかった場合、ブロックの最後に追加する
                            if not param_found:
                                # 新キーの場合はbonus.commonの下に無い場合、直下にフォールバック追加される
                                new_lines.append(f"    {new_key}: {value}\n")
                                updated = True
                            in_target_block = False
                    
                    # パラメータの書き換え
                    if in_target_block and stripped.startswith(f"{new_key}:"):
                        indent = line[:line.find(new_key)]
                        new_lines.append(f"{indent}{new_key}: {value}\n")
                        param_found = True
                        updated = True
                    else:
                        new_lines.append(line)
                
                # ファイルの最後がターゲットブロックで終わっている場合の処理
                if in_target_block and not param_found:
                    new_lines.append(f"    {new_key}: {value}\n")
                    updated = True
                
                if updated:
                    with open(path, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                    print(f"  [SURGICAL SAVE SUCCESS] {filename}: {target_id}.{new_key} -> {value}")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
                    return

            # もし上記で失敗した場合は、フォールバックとして以前の（コメント非保持）方式
            print(f"  [SAVE FALLBACK] Using naive yaml dump for {filename}")
            raw_data = load_master_data(filename)
            
            # データの更新
            updated = False
            if file_type == "enemies":
                for section in ["ENEMY_DATA", "ENEMY_CATEGORIES"]:
                    if section in raw_data and target_id in raw_data[section]:
                        raw_data[section][target_id][param] = value
                        updated = True; break
            elif file_type == "equipment":
                for section in ["WEAPON_DATA", "ARMOR_DATA", "SHIELD_DATA"]:
                    if section in raw_data and target_id in raw_data[section]:
                        item = raw_data[section][target_id]
                        if "bonus" not in item:
                            item["bonus"] = {"common": {}, "magic": {}}
                        if "common" not in item["bonus"]:
                            item["bonus"]["common"] = {}
                        new_key = KEY_MAP_TO_NEW.get(param, param)
                        item["bonus"]["common"][new_key] = value
                        updated = True; break
                
                if not updated:
                    for section in ["WEAPON_CATEGORIES", "ARMOR_CATEGORIES", "SHIELD_CATEGORIES"]:
                        if section in raw_data and target_id in raw_data[section]:
                            raw_data[section][target_id][param] = value
                            updated = True; break
            
            if updated:
                with open(path, "w", encoding="utf-8") as f:
                    yaml.dump(raw_data, f, allow_unicode=True, sort_keys=False, default_flow_style=None, indent=2)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            else:
                print(f"  [SAVE FAILED] Target ID '{target_id}' not found in {filename}")
                self.send_response(404)
                self.end_headers()

if __name__ == "__main__":
    # サーバーを起動するディレクトリをプロジェクトルートに合わせる
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"🚀 Dashboard Server running at http://localhost:{PORT}")
        print(f"Serving UI from: {os.path.join(DIRECTORY, 'dashboard.html')}")
        
        # 自動でブラウザを開く
        import webbrowser
        import threading
        def open_browser():
            import time
            time.sleep(0.5) # サーバー起動を待つ
            webbrowser.open(f"http://localhost:{PORT}")
        
        threading.Thread(target=open_browser, daemon=True).start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass



# 敵のタイプ	耐えられる回数	プレイ感
# ザコ（弱い）	8 〜 12発	1対1なら無傷〜軽傷。囲まれてもまだ余裕がある。
# 標準（普通）	4 〜 6発	1対1でも20%〜25%削られる。1対3で囲まれると「死」が見える緊張感。
# 強敵（強い）	2 〜 3発	出会った瞬間に「逃げるか、アイテムを使うか」を迫られる。ミスが許されない。
# バランス調整の黄金律
# おすすめは、「標準的な敵に1対1で勝ったとき、HPが 70% 〜 80% 残っている」 状態です。

# プレイヤーが2撃で敵を倒す
# その間に敵から1発食らう
# その1発でHPの 20% 〜 25% が減る（＝合計 4〜5発 で死ぬ）