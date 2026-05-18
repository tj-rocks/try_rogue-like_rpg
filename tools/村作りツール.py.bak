import http.server
import socketserver
import webbrowser
import threading
import os
import sys
import json

PORT = 8765
URL = f"http://localhost:{PORT}/tools/village_editor.html"

class EditorRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # ブラウザの強力なキャッシュを完全に無効化し、画像差し替えが即時反映されるようにする
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        if self.path == "/api/available_assets":
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if base_dir not in sys.path:
                    sys.path.append(base_dir)
                from systems.data_loader import load_master_data
                
                # Load assets directory dynamically from village.yml config
                village_data = load_master_data("village.yml") or {}
                config = village_data.get("CONFIG", {})
                image_dir_rel = config.get("image_dir", "components/pictures/dungeon/home")
                home_dir = os.path.join(base_dir, image_dir_rel)
                
                files = []
                if os.path.exists(home_dir):
                    files = [f for f in os.listdir(home_dir) if os.path.isfile(os.path.join(home_dir, f))]
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {"status": "success", "files": files}
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {"status": "error", "message": str(e)}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        elif self.path == "/api/tile_definitions":
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if base_dir not in sys.path:
                    sys.path.append(base_dir)
                from systems.data_loader import load_master_data
                
                # 1. Load base tile mappings and config from village.yml
                village_data = load_master_data("village.yml") or {}
                tile_mappings = village_data.get("TILE_MAPPINGS", {})
                config = village_data.get("CONFIG", {})
                

                # 2. Enrich NPCs and Obstacles dynamically using IDs defined in village.yml
                npcs = load_master_data("npcs.yml") or {}
                obstacles = load_master_data("obstacles.yml") or {}
                
                for char, tile in list(tile_mappings.items()):
                    if not isinstance(tile, dict): continue
                    category = tile.get("category")
                    entity_id = tile.get("id")
                    if not entity_id: continue
                    
                    if category == "npc":
                        data = npcs.get(entity_id)
                        if data:
                            img = data.get("image_path", "")
                            # Check file naming rules for guide NPCs vs normal NPCs
                            if os.path.exists(os.path.join(base_dir, img, "0.png")):
                                image_file = "0.png"
                            else:
                                image_file = "idel.png"
                            
                            tile["image_path"] = f"{img}/{image_file}" if img else ""
                            tile["bg_image_path"] = tile.get("base_image_path", data.get("base_image_path", "components/pictures/dungeon/home/floor_1.png"))
                            tile["bg_color"] = tile.get("bg_color", "#3a2a1a")
                            tile["fg_color"] = tile.get("fg_color", "#ffbb88")
                            tile["desc"] = data.get("name", tile.get("desc"))
                            
                    elif category == "obstacle":
                        data = obstacles.get(entity_id)
                        if data:
                            tile["image_path"] = data.get("image_path", "")
                            tile["bg_image_path"] = tile.get("base_image_path", data.get("base_image_path", "components/pictures/dungeon/home/floor_0.png"))
                            tile["bg_color"] = tile.get("bg_color", "#4a2a1a")
                            tile["fg_color"] = tile.get("fg_color", "#aa5a3a")
                            tile["desc"] = data.get("name", tile.get("desc"))
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {"status": "success", "tiles": tile_mappings, "config": config}
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {"status": "error", "message": str(e)}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/save_village":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                text_content = data.get('content', '')
                
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if base_dir not in sys.path:
                    sys.path.append(base_dir)
                from systems.data_loader import load_master_data
                
                # Load map file settings dynamically from village.yml config
                village_data = load_master_data("village.yml") or {}
                config = village_data.get("CONFIG", {})
                default_map = config.get("map_file", "village.txt")
                map_dir_rel = config.get("map_dir", "components/data/dungeon")
                
                # クライアントから送信されたファイル名を取得する
                filename = os.path.basename(data.get('filename', default_map))
                if not filename.endswith('.txt'):
                    filename = default_map
                
                # マップの絶対パスを解決する
                village_path = os.path.join(base_dir, map_dir_rel, filename)
                
                # ファイルに書き込む
                with open(village_path, "w", encoding="utf-8") as f:
                    f.write(text_content)
                
                # 正常終了のレスポンス
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {"status": "success", "message": f"Successfully saved map directly to {filename}!"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                print(f"\n[SERVER] ✅ マップ変更が {village_path} に直接上書き保存されました！")
            except Exception as e:
                # エラー発生時のレスポンス
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {"status": "error", "message": str(e)}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                print(f"\n[SERVER] ❌ 保存エラー: {str(e)}")
        else:
            self.send_response(404)
            self.end_headers()

    # CORSプリフライト（OPTIONSリクエスト）への対応
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def start_server():
    # プロジェクトルート（toolsの1つ上）にカレントディレクトリを合わせる
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base_dir)
    
    # 既にポートが使われている場合の処理
    try:
        # スレッド対応のTCPServerを作成
        class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            allow_reuse_address = True
            
        with ThreadedTCPServer(("", PORT), EditorRequestHandler) as httpd:
            print(f"🚀 村マップグラフィックエディタ用サーバーをポート {PORT} で起動しました。")
            print(f"📂 作業ディレクトリ: {base_dir}")
            print(f"🌐 ブラウザで開いています: {URL}")
            
            # ブラウザを1秒後に開く（サーバー起動完了を待つため）
            threading.Timer(1.0, lambda: webbrowser.open(URL)).start()
            
            print("\n[Ctrl+C でサーバーを終了します]")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 48: # Address already in use
            print(f"⚠️  ポート {PORT} は既に使用されています。ブラウザでそのまま開きます。")
            webbrowser.open(URL)
        else:
            raise e

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n👋 サーバーを終了しました。")
        sys.exit(0)
