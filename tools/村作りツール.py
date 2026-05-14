import http.server
import socketserver
import webbrowser
import threading
import os
import sys
import time

PORT = 8765
# village_editor.html への相対パス（tools ディレクトリ内にあることを想定）
URL = f"http://localhost:{PORT}/tools/village_editor.html"

def start_server():
    # プロジェクトルート（toolsの1つ上）にカレントディレクトリを合わせる
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base_dir)
    
    Handler = http.server.SimpleHTTPRequestHandler
    
    # 既にポートが使われている場合の処理
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"🚀 村マップエディタ用サーバーをポート {PORT} で起動しました。")
            print(f"📂 作業ディレクトリ: {base_dir}")
            print(f"🌐 ブラウザで開いています: {URL}")
            
            # ブラウザを1秒後に開く（サーバー起動完了を待つため）
            threading.Timer(1, lambda: webbrowser.open(URL)).start()
            
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
