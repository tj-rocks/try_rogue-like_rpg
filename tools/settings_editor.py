#!/usr/bin/env python3
"""
🎮 ゲーム設定エディター (JSON版)
JSONファイルを直接読み書きするクリーンな実装になりました。
"""
import json, os, signal, subprocess, threading, webbrowser, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "components/data/master")
HTML_PATH = os.path.join(PROJECT_ROOT, "tools/web/settings_editor.html")
PORT = 8765

FILES = {
    "balance": "balance.json",
    "enemies": "enemies.json",
    "equipment": "equipment.json",
    "items": "items.json",
    "dungeon": "dungeon.json"
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def get_all_data(self):
        """master フォルダ内の全 JSON/YAML ファイルを読み込んで返す"""
        all_data = {}
        if not os.path.exists(DATA_DIR):
            return all_data
        
        for filename in os.listdir(DATA_DIR):
            ext = os.path.splitext(filename)[1].lower()
            if ext in (".json", ".yml", ".yaml"):
                path = os.path.join(DATA_DIR, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        key = os.path.splitext(filename)[0]
                        if ext in (".yml", ".yaml"):
                            import yaml
                            all_data[key] = yaml.safe_load(f)
                        else:
                            all_data[key] = json.load(f)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        return all_data

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(HTML_PATH, "rb") as f: content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content)
        elif self.path == "/api/data":
            self._json(self.get_all_data())
        elif self.path == "/api/assets":
            def get_assets(sub):
                root_path = os.path.join(PROJECT_ROOT, sub)
                res = {"files": [], "dirs": []}
                if not os.path.exists(root_path): return res
                for root, dirs, files in os.walk(root_path):
                    rel = os.path.relpath(root, PROJECT_ROOT)
                    for d in dirs:
                        if not d.startswith('.'):
                            res["dirs"].append(os.path.join(rel, d))
                    for f in files:
                        if not f.startswith('.'):
                            res["files"].append(os.path.join(rel, f))
                res["files"].sort()
                res["dirs"].sort()
                return res
            
            self._json({
                "pictures": get_assets("components/pictures"),
                "sounds": get_assets("components/sounds")
            })
        elif self.path.startswith("/img"):
            parsed = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(parsed.query)
            if "path" in q:
                path = q["path"][0]
                full_path = os.path.join(PROJECT_ROOT, path)
                
                # もしディレクトリなら、代表的な画像を探す
                if os.path.isdir(full_path):
                    # 候補: down.png, down_1.png, (dir_name).png, フォルダ内の最初のpng
                    candidates = ["down.png", "down_1.png", f"{os.path.basename(full_path)}.png"]
                    found = False
                    for c in candidates:
                        cp = os.path.join(full_path, c)
                        if os.path.exists(cp):
                            full_path = cp
                            found = True
                            break
                    if not found:
                        for f in os.listdir(full_path):
                            if f.lower().endswith(".png"):
                                full_path = os.path.join(full_path, f)
                                found = True
                                break
                
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    with open(full_path, "rb") as f:
                        img_data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.end_headers()
                    self.wfile.write(img_data)
                    return
            self.send_response(404); self.end_headers()
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        if self.path == "/api/save":
            try:
                payload = json.loads(post_data)
                for key, content in payload.items():
                    path = os.path.join(DATA_DIR, f"{key}.yml")
                    if not os.path.exists(path):
                        path = os.path.join(DATA_DIR, f"{key}.yaml")
                    if not os.path.exists(path):
                        path = os.path.join(DATA_DIR, f"{key}.json")
                    
                    ext = os.path.splitext(path)[1].lower()
                    with open(path, "w", encoding="utf-8") as f:
                        if ext in (".yml", ".yaml"):
                            import yaml
                            yaml.safe_dump(content, f, allow_unicode=True, sort_keys=False)
                        else:
                            json.dump(content, f, ensure_ascii=False, indent=4)
                self._json({"ok": True, "message": "すべての設定を保存しました！"})
            except Exception as e:
                self._json({"ok": False, "message": str(e)}, 500)
        elif self.path == "/api/upload":
            try:
                ctype = self.headers.get('Content-Type')
                if 'boundary=' in ctype:
                    boundary = ctype.split('boundary=')[1].encode()
                    parts = post_data.split(b'--' + boundary)
                    for part in parts:
                        if b'filename="' in part:
                            h_end = part.find(b'\r\n\r\n')
                            headers = part[:h_end].decode()
                            import re
                            filename = re.search(r'filename="([^"]+)"', headers).group(1)
                            save_dir = os.path.join(PROJECT_ROOT, "components/pictures/uploads")
                            os.makedirs(save_dir, exist_ok=True)
                            save_path = os.path.join(save_dir, filename)
                            content = part[h_end+4:].rstrip(b'\r\n--').rstrip(b'\r\n')
                            with open(save_path, "wb") as f:
                                f.write(content)
                            rel_path = os.path.relpath(save_path, PROJECT_ROOT)
                            self._json({"ok": True, "path": rel_path})
                            return
                self._json({"ok": False, "message": "No file found"}, 400)
            except Exception as e:
                self._json({"ok": False, "message": str(e)}, 500)
        else:
            self.send_response(404); self.end_headers()

def _kill_port(port: int):
    try:
        r = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
        for pid in r.stdout.strip().split("\n"):
            if pid: os.kill(int(pid), signal.SIGTERM)
    except Exception: pass

def main():
    _kill_port(PORT)
    print(f"🚀 Editor running at http://localhost:{PORT}")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    server = HTTPServer(("localhost", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye!")

if __name__ == "__main__":
    main()
