
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
            weapons, armor, shields, w_types = get_normalized_equipment_data(floor_map)
            
            print(f"[API] Normalized {len(enemies)} enemies, {len(weapons)} weapons, {len(armor)} armors")
            
            data = {
                "balance": balance_cfg,
                "guild": guild_data,
                "enemies": enemies,
                "weapons": weapons,
                "armor": armor,
                "shields": shields,
                "raw_enemies": load_master_data("enemies.yml"),
                "raw_equipment": load_master_data("equipment.yml")
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

            updated = False
            # データの更新
            if file_type == "enemies":
                for section in ["ENEMY_DATA", "ENEMY_CATEGORIES"]:
                    if section in raw_data and target_id in raw_data[section]:
                        raw_data[section][target_id][param] = value
                        updated = True; break
            elif file_type == "equipment":
                for section in ["WEAPON_DATA", "ARMOR_DATA", "SHIELD_DATA", "WEAPON_CATEGORIES", "ARMOR_CATEGORIES"]:
                    if section in raw_data and target_id in raw_data[section]:
                        raw_data[section][target_id][param] = value
                        updated = True; break
            
            if updated:
                path = os.path.join(MASTER_DATA_DIR, filename)
                with open(path, "w", encoding="utf-8") as f:
                    # 短いリストを [x, y] 形式で出力するための設定
                    yaml.dump(raw_data, f, allow_unicode=True, sort_keys=False, default_flow_style=None, indent=2)
                
                # 詳細なログを出力
                print(f"  [SAVE SUCCESS] {filename}: {target_id}.{param} -> {value}")
                
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