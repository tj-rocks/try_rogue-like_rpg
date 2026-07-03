import http.server
import socketserver
import webbrowser
import threading
import os
import sys
import json
import glob

PORT = 8765
URL = f"http://localhost:{PORT}/tools/village_editor.html"


def _get_theme_for_map(map_file):
    """dungeon.yml から map_file に対応するテーマ(image)を返す。村は home。"""
    if map_file == "village.txt":
        return "home"
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if base_dir not in sys.path:
        sys.path.append(base_dir)
    from systems.data_loader import load_master_data
    dungeon_data = load_master_data("dungeon.yml") or {}
    dungeon_images = dungeon_data.get("DUNGEON_IMAGES", {})
    for key, info in dungeon_images.items():
        if key in ("path", "bgm_path"):
            continue
        if isinstance(info, dict) and info.get("map") == map_file:
            return info.get("image", "home")
    return "home"


def _get_theme_image_path(theme_dir, category, tile_id=0):
    """テーマディレクトリ内から category/tile_id に対応する画像ファイル名を返す。"""
    candidates = []
    fallback_pattern = None
    if category == "floor":
        candidates = [f"floor_{tile_id}.png", "floor.png"]
        fallback_pattern = "floor_*.png"
    elif category == "wall_top":
        candidates = [f"wall_top_{tile_id}.png", "wall_top.png"]
        fallback_pattern = "wall_top_*.png"
    elif category == "wall_none":
        candidates = [f"wall_none_{tile_id}.png", "wall_none.png"]
        fallback_pattern = "wall_none_*.png"
    elif category == "corridor":
        candidates = ["corridor.png"]
        fallback_pattern = "floor_*.png"
    elif category == "wall_pass":
        candidates = [f"wall_pass_{tile_id}.png", "wall_pass.png", "wall_top.png"]
        fallback_pattern = "wall_top_*.png"
    else:
        return None
    for c in candidates:
        if os.path.exists(os.path.join(theme_dir, c)):
            return c
    if fallback_pattern:
        matches = sorted(glob.glob(os.path.join(theme_dir, fallback_pattern)))
        if matches:
            return os.path.basename(matches[0])
    return None


def _resolve_tile_image_path_for_theme(base_dir, tile, theme):
    """タイル定義を theme 用に image_path を上書きして返す（theme カテゴリのみ）。"""
    if not isinstance(tile, dict):
        return tile
    category = tile.get("category")
    if category not in ("floor", "wall_top", "wall_none", "corridor", "wall_pass"):
        return tile
    tile_id = tile.get("tile_id", 0)
    theme_dir = os.path.join(base_dir, "components/pictures/dungeon", theme)
    filename = _get_theme_image_path(theme_dir, category, tile_id)
    if filename:
        new_tile = dict(tile)
        new_tile["image_path"] = f"components/pictures/dungeon/{theme}/{filename}"
        return new_tile
    return tile

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
                import urllib.parse
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if base_dir not in sys.path:
                    sys.path.append(base_dir)
                from systems.data_loader import load_master_data
                
                parsed_url = urllib.parse.urlparse(self.path)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                theme = query_params.get("theme", [None])[0]
                if not theme:
                    map_file = os.path.basename(query_params.get("map_file", ["village.txt"])[0])
                    theme = _get_theme_for_map(map_file)
                
                # Load assets directory dynamically from the selected theme
                image_dir = os.path.join(base_dir, "components/pictures/dungeon", theme)
                
                files = []
                if os.path.exists(image_dir):
                    files = [f for f in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, f))]
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {"status": "success", "files": files, "theme": theme}
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {"status": "error", "message": str(e)}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        elif self.path == "/api/available_maps":
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if base_dir not in sys.path:
                    sys.path.append(base_dir)
                from systems.data_loader import load_master_data
                
                village_data = load_master_data("village.yml") or {}
                config = village_data.get("CONFIG", {})
                map_dir_rel = config.get("map_dir", "components/data/dungeon")
                map_dir = os.path.join(base_dir, map_dir_rel)
                
                files = []
                if os.path.exists(map_dir):
                    files = [f for f in os.listdir(map_dir) 
                             if os.path.isfile(os.path.join(map_dir, f)) 
                             and f.endswith('.txt') and not f.startswith('.')]
                files.sort()
                
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
        elif self.path.startswith("/api/tile_definitions"):
            try:
                import urllib.parse
                parsed_url = urllib.parse.urlparse(self.path)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                map_file = os.path.basename(query_params.get("map_file", ["village.txt"])[0])
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if base_dir not in sys.path:
                    sys.path.append(base_dir)
                from systems.data_loader import load_master_data
                
                # Base is always village.yml
                village_data = load_master_data("village.yml") or {}
                base_mappings = village_data.get("TILE_MAPPINGS", {})
                config = village_data.get("CONFIG", {})
                
                # Determine theme for this map from dungeon.yml
                theme = _get_theme_for_map(map_file)
                config = dict(config)
                config["image_dir"] = f"components/pictures/dungeon/{theme}"
                config["theme"] = theme
                
                # Look for custom config
                custom_file = None
                if map_file != "village.txt":
                    candidate = f"restpoint/{map_file.replace('.txt', '.yml')}"
                    if os.path.exists(os.path.join(base_dir, "components/data/master", candidate)):
                        custom_file = candidate
                
                tile_mappings = {}
                is_village_map = (map_file == "village.txt")
                
                if custom_file:
                    custom_data = load_master_data(custom_file) or {}
                    custom_mappings = custom_data.get("TILE_MAPPINGS", {})
                    for k, v in base_mappings.items():
                        if isinstance(v, dict):
                            tile_mappings[k] = dict(v)
                            if k in custom_mappings and isinstance(custom_mappings[k], dict):
                                if "positions" in custom_mappings[k]:
                                    tile_mappings[k]["positions"] = custom_mappings[k]["positions"]
                                else:
                                    tile_mappings[k].pop("positions", None)
                            else:
                                tile_mappings[k].pop("positions", None)
                    # Load any additional map-specific custom mappings not present in base
                    for k, v in custom_mappings.items():
                        if isinstance(v, dict) and k not in tile_mappings:
                            tile_mappings[k] = dict(v)
                else:
                    for k, v in base_mappings.items():
                        if isinstance(v, dict):
                            tile_mappings[k] = dict(v)
                            # Clear positions for rest points / custom maps if no custom yml exists
                            if not is_village_map:
                                tile_mappings[k].pop("positions", None)
                
                # 2. rest point 等の非村固定マップでは dungeon.yml のテーマ画像を使う
                if not is_village_map:
                    for k, tile in tile_mappings.items():
                        if isinstance(tile, dict):
                            tile_mappings[k] = _resolve_tile_image_path_for_theme(base_dir, tile, theme)

                # 3. Enrich NPCs / Obstacles / Enemies dynamically using IDs defined in village.yml
                npcs = load_master_data("npcs.yml") or {}
                obstacles = load_master_data("obstacles.yml") or {}
                enemies_raw = load_master_data("enemies.yml") or {}
                enemies = enemies_raw.get("ENEMY_DATA", {})
                
                for char, tile in list(tile_mappings.items()):
                    if not isinstance(tile, dict): continue
                    category = tile.get("category")
                    entity_id = tile.get("id")
                    if not entity_id: continue
                    
                    if category == "npc":
                        data = npcs.get(entity_id)
                        if data:
                            img = data.get("image_path", "")
                            # image_path が辞書形式（ランク別）の場合は "default" キーを優先して使う
                            if isinstance(img, dict):
                                img = img.get("default") or next(iter(img.values()), "")
                            img = img or ""
                            # Check file naming rules for guide NPCs vs normal NPCs
                            if os.path.exists(os.path.join(base_dir, str(img), "0.png")):
                                image_file = "0.png"
                            else:
                                image_file = "idel.png"
                            
                            tile["image_path"] = f"{img}/{image_file}" if img else ""
                            tile["desc"] = data.get("name", tile.get("desc"))
                            tile["dialogue"] = data.get("dialogue", [])
                            # 施設NPC(role有) vs セリフだけのNPC(role無) を区別
                            role = data.get("role")
                            if role:
                                tile["subcategory"] = "npc_facility"
                                tile["role"] = role
                            else:
                                tile["subcategory"] = "npc_dialogue"
                            
                    elif category == "obstacle":
                        data = obstacles.get(entity_id)
                        if data:
                            tile["image_path"] = data.get("image_path", "")
                            tile["desc"] = data.get("name", tile.get("desc"))

                    elif category == "enemy":
                        data = enemies.get(entity_id)
                        if data:
                            img = data.get("image_path", "")
                            if not img:
                                folder = data.get("image_folder", "")
                                if folder:
                                    for candidate in ("down.png", "left.png", "up.png", "right.png"):
                                        candidate_path = os.path.join(base_dir, folder, candidate)
                                        if os.path.exists(candidate_path):
                                            img = f"{folder}/{candidate}"
                                            break
                            tile["image_path"] = img
                            tile["desc"] = data.get("name", tile.get("desc", entity_id))
                            tile["subcategory"] = "enemy_boss" if data.get("is_boss") else "enemy"

                    elif category == "wall_decoration":
                        image_path = tile.get("image_path")
                        if not image_path:
                            image_path = "components/pictures/dungeon/shallow/wall_decoration_0.png"
                        tile["image_path"] = image_path
                        tile["desc"] = tile.get("desc", "壁装飾")
                
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
                
                # クライアントから送信されたentitiesを受け取る
                entities = data.get('entities', [])
                
                # グループ化 (idをキーにする)
                grouped = {}
                for e in entities:
                    ent_id = e.get('id')
                    if ent_id:
                        pos_entry = {'x': e['x'], 'y': e['y'], 'flip': e.get('flip', False)}
                        if e.get('min_rank'):
                            pos_entry['min_rank'] = e['min_rank']
                        if e.get('max_rank'):
                            pos_entry['max_rank'] = e['max_rank']
                        grouped.setdefault(ent_id, []).append(pos_entry)

                master_file = "village.yml"
                target_file = "village.yml"
                if filename != "village.txt":
                    candidate = f"restpoint/{filename.replace('.txt', '.yml')}"
                    target_file = candidate
                    if os.path.exists(os.path.join(base_dir, "components/data/master", candidate)):
                        master_file = candidate
                    else:
                        master_file = "village.yml"
                
                load_path = os.path.join(base_dir, "components", "data", "master", master_file)
                save_path = os.path.join(base_dir, "components", "data", "master", target_file)
                
                # Ensure the parent directory for restpoints exists
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                try:
                    import importlib
                    ruamel_yaml = importlib.import_module("ruamel.yaml")
                    YAML = ruamel_yaml.YAML
                    has_ruamel = True
                except ImportError:
                    import yaml as pyyaml
                    has_ruamel = False
                    
                    class IndentedSafeDumper(pyyaml.SafeDumper):
                        def increase_indent(self, flow=False, indentless=False):
                            return super(IndentedSafeDumper, self).increase_indent(flow, False)
                
                if has_ruamel:
                    yaml = YAML()
                    yaml.preserve_quotes = True
                    yaml.indent(mapping=2, sequence=4, offset=2)
                    with open(load_path, "r", encoding="utf-8") as f:
                        village_yml_data = yaml.load(f)
                else:
                    with open(load_path, "r", encoding="utf-8") as f:
                        village_yml_data = pyyaml.safe_load(f) or {}
                
                # positionsを各定義に注入
                mappings = village_yml_data.get("TILE_MAPPINGS", {})
                is_new_file = (load_path != save_path)

                # restpoint YMLが既に存在する場合、village.ymlにないカスタム定義を保持する
                if is_new_file and os.path.exists(save_path):
                    try:
                        if has_ruamel:
                            yaml_r = YAML()
                            yaml_r.preserve_quotes = True
                            with open(save_path, "r", encoding="utf-8") as f:
                                existing_data = yaml_r.load(f)
                        else:
                            with open(save_path, "r", encoding="utf-8") as f:
                                existing_data = pyyaml.safe_load(f) or {}
                        existing_mappings = existing_data.get("TILE_MAPPINGS", {}) if existing_data else {}
                        for ek, ev in existing_mappings.items():
                            if ek not in mappings and isinstance(ev, dict):
                                mappings[ek] = ev
                    except Exception:
                        pass

                for k, v in mappings.items():
                    if not isinstance(v, dict):
                        continue
                    
                    # If this is a new config file created from village.yml template,
                    # we must first purge any inherited village positions to start fresh.
                    if is_new_file and "positions" in v:
                        del v["positions"]
                        
                    if k in grouped:
                        v["positions"] = grouped[k]
                    else:
                        if "positions" in v:
                            del v["positions"]
                
                # YMLに未定義だがエディタで配置されたNPCエントリを自動追加
                # (village.yml経由で新しく追加されたNPC等がここで保存される)
                base_npcs = load_master_data("npcs.yml") or {}
                base_enemies = (load_master_data("enemies.yml") or {}).get("ENEMY_DATA", {})
                for ent_id, positions in grouped.items():
                    if ent_id not in mappings:
                        # npcs.ymlにあるNPCならcategory=npcで追加
                        if ent_id in base_npcs:
                            mappings[ent_id] = {"category": "npc", "id": ent_id, "positions": positions}
                        elif ent_id in base_enemies:
                            mappings[ent_id] = {"category": "enemy", "id": ent_id, "positions": positions}
                        else:
                            # obstacleやwall_decorationは village.yml のベースから探す
                            base_mappings = (load_master_data("village.yml") or {}).get("TILE_MAPPINGS", {})
                            if ent_id in base_mappings and isinstance(base_mappings[ent_id], dict):
                                entry = dict(base_mappings[ent_id])
                                entry.pop("positions", None)  # village座標は使わない
                                entry["positions"] = positions
                                mappings[ent_id] = entry
                
                # 古いENTITIESブロック（もし残っていれば）を完全に排除
                if "ENTITIES" in village_yml_data:
                    del village_yml_data["ENTITIES"]
                
                if has_ruamel:
                    with open(save_path, "w", encoding="utf-8") as f:
                        yaml.dump(village_yml_data, f)
                else:
                    with open(save_path, "w", encoding="utf-8") as f:
                        pyyaml.dump(village_yml_data, f, Dumper=IndentedSafeDumper, allow_unicode=True, sort_keys=False, indent=2)
                
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
