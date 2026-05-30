import http.server
import socketserver
import json
import os
import sys
import yaml

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from systems.data_loader import MASTER_DATA_DIR, load_master_data

PORT = 5010
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class AutoBalancerHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/' or self.path == '/auto_balancer.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            ui_path = os.path.join(DIRECTORY, 'auto_balancer.html')
            with open(ui_path, 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # YAMLの生データをロードして返す
            enemies_path = os.path.join(MASTER_DATA_DIR, "enemies.yml")
            with open(enemies_path, 'r', encoding='utf-8') as f:
                raw_enemies = yaml.safe_load(f) or {}

            weapons_path = os.path.join(MASTER_DATA_DIR, "weapons.yml")
            with open(weapons_path, 'r', encoding='utf-8') as f:
                raw_weapons = yaml.safe_load(f) or {}

            data = {
                "enemies": raw_enemies.get("ENEMY_DATA", {}),
                "weapons": raw_weapons.get("WEAPON_DATA", {})
            }
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/auto-apply':
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length).decode('utf-8'))
            
            updated_enemies = post_data.get("enemies")
            if not updated_enemies:
                self.send_response(400)
                self.end_headers()
                return

            enemies_path = os.path.join(MASTER_DATA_DIR, "enemies.yml")
            with open(enemies_path, 'r', encoding='utf-8') as f:
                raw_data = yaml.safe_load(f) or {}

            # 生のYAML構造を維持したまま、HP/攻撃/防御/命中/回避を更新
            if "ENEMY_DATA" in raw_data:
                for enemy_id, stats in updated_enemies.items():
                    if enemy_id in raw_data["ENEMY_DATA"]:
                        target_enemy = raw_data["ENEMY_DATA"][enemy_id]
                        # 整数にキャストしてクランプ
                        target_enemy["hp"] = max(1, int(stats.get("hp", target_enemy.get("hp", 1))))
                        target_enemy["attack"] = max(1, int(stats.get("attack", target_enemy.get("attack", 1))))
                        target_enemy["defense"] = max(0, int(stats.get("defense", target_enemy.get("defense", 0))))
                        target_enemy["evasion"] = max(0, int(stats.get("evasion", target_enemy.get("evasion", 0))))
                        target_enemy["accuracy_close"] = max(1, int(stats.get("accuracy_close", target_enemy.get("accuracy_close", 100))))
                
                with open(enemies_path, "w", encoding="utf-8") as f:
                    yaml.dump(raw_data, f, allow_unicode=True, sort_keys=False, default_flow_style=None, indent=2)
                
                print("🚀 [AUTO-BALANCER] Successfully applied new stats to enemies.yml!")
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            else:
                self.send_response(500)
                self.end_headers()

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    socketserver.TCPServer.allow_reuse_address = True
    
    httpd = None
    for p in range(PORT, PORT + 10):
        try:
            httpd = socketserver.TCPServer(("", p), AutoBalancerHandler)
            PORT = p
            break
        except OSError as e:
            if e.errno == 48 or "[Errno 48]" in str(e):
                print(f"⚠️ Port {p} is already in use. Trying port {p + 1}...")
                continue
            raise e

    if not httpd:
        print("❌ Error: Could not find an available port to bind the Auto-Balancer server.")
        sys.exit(1)
        
    with httpd:
        print(f"🚀 Auto-Balancer Server running at http://localhost:{PORT}")
        print(f"Serving UI from: {os.path.join(DIRECTORY, 'auto_balancer.html')}")
        
        import webbrowser
        import threading
        def open_browser():
            import time
            time.sleep(0.5)
            webbrowser.open(f"http://localhost:{PORT}")
        
        threading.Thread(target=open_browser, daemon=True).start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
