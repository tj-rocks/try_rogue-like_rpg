#!/bin/bash
# restore_backup.sh - テスト失敗などで残ってしまったバックアップを強制的に復元する
# 
# 使い方: ./tools/scripts/restore_backup.sh

OFFICIAL_SAVE="components/data/savefile/save_official.json"
BACKUP_SAVE="components/data/savefile/save_official.json.bak"

if [ -f "$BACKUP_SAVE" ]; then
    echo "📦 バックアップファイル ($BACKUP_SAVE) を見つけました。"
    if [ -f "$OFFICIAL_SAVE" ]; then
        echo "⚠️  注意: すでに本番用ファイルが存在します。上書きしますか？ (y/n)"
        read -r choice
        if [ "$choice" != "y" ]; then
            echo "❌ 中止しました。"
            exit 1
        fi
    fi
    mv "$BACKUP_SAVE" "$OFFICIAL_SAVE"
    echo "✅ 復元が完了しました。"
else
    echo "ℹ️  バックアップファイルは見つかりませんでした。隔離状態は正常です。"
fi
