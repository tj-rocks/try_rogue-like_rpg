---
description: メインロジック変更後に自動テストを実行する
---

## メインロジック変更後のテスト実行

以下のいずれかを変更した場合に実行:
- `systems/` 配下の `.py` ファイル
- `components/` 配下の `.py` ファイル
- `constants.py` / `dependencies.py` / `wordings.py`
- `main.py`

### 手順

1. テストスイートを実行する
```bash
cd /Users/tj/Desktop/2DGame && TEST_MODE=1 ./tests/run_tests.sh
```

### 例外（テスト不要）

- `tools/` 配下のデバッグツール類（`ダンジョン系のデバッグ.py` 等）の修正は、自動テスト対象外のため実行不要
