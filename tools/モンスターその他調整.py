import http.server
import socketserver
import json
import os
import sys
import yaml

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from systems.data_loader import MASTER_DATA_DIR, load_master_data

PORT = 5020
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

def load_all_items():
    """ゲーム内の全マスターデータからアイテムキーと日本語表示名のマッピングを作成する"""
    items_map = {} # key -> name
    
    # 1. items.yml (CONSUMABLE_DATA, STAVE_DATA, LANTERN_DATA)
    try:
        items_data = load_master_data("items.yml") or {}
        for group in ["CONSUMABLE_DATA", "STAVE_DATA", "LANTERN_DATA"]:
            data = items_data.get(group, {})
            for k, v in data.items():
                if isinstance(v, dict) and "name" in v:
                    items_map[k] = v["name"]
    except Exception as e:
        print(f"Error loading items.yml: {e}")
                
    # 2. weapons.yml (WEAPON_DATA)
    try:
        weapons_data = load_master_data("weapons.yml") or {}
        data = weapons_data.get("WEAPON_DATA", {})
        for k, v in data.items():
            if isinstance(v, dict) and "name" in v:
                items_map[k] = v["name"]
    except Exception as e:
        print(f"Error loading weapons.yml: {e}")
            
    # 3. armors.yml (ARMOR_DATA)
    try:
        armors_data = load_master_data("armors.yml") or {}
        data = armors_data.get("ARMOR_DATA", {})
        for k, v in data.items():
            if isinstance(v, dict) and "name" in v:
                items_map[k] = v["name"]
    except Exception as e:
        print(f"Error loading armors.yml: {e}")
            
    # 4. shields.yml (SHIELD_DATA)
    try:
        shields_data = load_master_data("shields.yml") or {}
        data = shields_data.get("SHIELD_DATA", {})
        for k, v in data.items():
            if isinstance(v, dict) and "name" in v:
                items_map[k] = v["name"]
    except Exception as e:
        print(f"Error loading shields.yml: {e}")
            
    # 特殊アイテム
    items_map["gold"] = "ゴールド"
            
    return items_map

class MonsterEditorHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/' or self.path == '/monster_editor.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            ui_path = os.path.join(DIRECTORY, 'monster_editor.html')
            with open(ui_path, 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # enemies.yml の生データをロード
            enemies_path = os.path.join(MASTER_DATA_DIR, "enemies.yml")
            with open(enemies_path, 'r', encoding='utf-8') as f:
                raw_enemies = yaml.safe_load(f) or {}

            # 全アイテムのマスター辞書をロード
            items_master = load_all_items()

            data = {
                "enemies": raw_enemies.get("ENEMY_DATA", {}),
                "items": items_master
            }
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/save':
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

            if "ENEMY_DATA" in raw_data:
                for enemy_id, stats in updated_enemies.items():
                    if enemy_id in raw_data["ENEMY_DATA"]:
                        target = raw_data["ENEMY_DATA"][enemy_id]
                        
                        # 1. 基本・テキスト
                        target["name"] = stats.get("name", target.get("name", "モンスター"))
                        target["min_rank"] = stats.get("min_rank", target.get("min_rank", "F"))
                        
                        # 2. AI・視野
                        if "stupidity" in stats:
                            target["stupidity"] = int(stats["stupidity"])
                        if "detect_range" in stats:
                            target["detect_range"] = int(stats["detect_range"])
                        if "damaged_detect_range" in stats:
                            target["damaged_detect_range"] = int(stats["damaged_detect_range"])
                            
                        # 3. 報酬
                        if "reward_gold" in stats:
                            target["reward_gold"] = int(stats["reward_gold"])
                        if "exp" in stats:
                            target["exp"] = int(stats["exp"])
                            
                        # 4. アセット・スケーリング
                        target["image_folder"] = stats.get("image_folder", target.get("image_folder", ""))
                        
                        color = stats.get("image_color", "").strip()
                        if color:
                            target["image_color"] = color
                        elif "image_color" in target:
                            del target["image_color"]
                            
                        if "image_scale" in stats:
                            target["image_scale"] = float(stats["image_scale"])
                            
                        # 5. ボスタグ
                        is_boss = stats.get("is_boss", False)
                        if is_boss:
                            target["is_boss"] = True
                        elif "is_boss" in target:
                            del target["is_boss"]
                            
                        # 6. ドロップ設定
                        if "drops" in stats:
                            new_drops = stats["drops"]
                            drops_struct = {}
                            if new_drops.get("normal"):
                                drops_struct["normal"] = new_drops["normal"]
                            if new_drops.get("rare"):
                                drops_struct["rare"] = new_drops["rare"]
                                
                            if drops_struct:
                                target["drops"] = drops_struct
                            elif "drops" in target:
                                del target["drops"]
                                
                        if "normal_drop_rate" in stats:
                            target["normal_drop_rate"] = float(stats["normal_drop_rate"])
                        if "rare_drop_rate" in stats:
                            target["rare_drop_rate"] = float(stats["rare_drop_rate"])
                
                # YAML形式で美しく書き出し
                with open(enemies_path, "w", encoding="utf-8") as f:
                    yaml.dump(raw_data, f, allow_unicode=True, sort_keys=False, default_flow_style=None, indent=2)
                
                print("🚀 [MONSTER-EDITOR] Successfully saved other configurations to enemies.yml!")
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
            httpd = socketserver.TCPServer(("", p), MonsterEditorHandler)
            PORT = p
            break
        except OSError as e:
            if e.errno == 48 or "[Errno 48]" in str(e):
                print(f"⚠️ Port {p} is already in use. Trying port {p + 1}...")
                continue
            raise e

    if not httpd:
        print("❌ Error: Could not find an available port to bind the Monster Editor server.")
        sys.exit(1)
        
    with httpd:
        print(f"🚀 Monster Editor Server running at http://localhost:{PORT}")
        print(f"Serving UI from: {os.path.join(DIRECTORY, 'monster_editor.html')}")
        
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
