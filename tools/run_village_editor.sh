#!/bin/bash
# 村マップエディタを起動するスクリプト

PORT=8765
URL="http://localhost:$PORT/tools/village_editor.html"

echo "🚀 村マップエディタ用サーバーをポート $PORT で起動します..."

# 既にポートが使われている場合は警告
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  ポート $PORT は既に使用されています。ブラウザでそのまま開きます。"
else
    # バックグラウンドでサーバー起動
    python3 -m http.server $PORT &
    SERVER_PID=$!
    # スクリプト終了時にサーバーも止める場合は trap を使う
    trap "kill $SERVER_PID" EXIT
    sleep 1
fi

echo "🌐 ブラウザでエディタを開きます: $URL"
open "$URL"

# サーバーを維持するために待機
wait
