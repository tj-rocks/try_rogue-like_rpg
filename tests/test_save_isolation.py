import os
import time
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_save_isolation():
    print("--- セーブデータ隔離テスト ---")
    
    # 1. TEST_MODE 環境変数のチェック
    test_mode = os.environ.get("TEST_MODE")
    if test_mode != "1":
        print(f"❌ エラー: TEST_MODE が '1' ではありません (現在の値: {test_mode})")
        sys.exit(1)
    
    # 2. data_loader からパスを取得してチェック
    from systems.data_loader import SAVE_OFFICIAL_PATH
    save_filename = os.path.basename(SAVE_OFFICIAL_PATH)
    
    if "save_official.json" in save_filename:
        print(f"❌ エラー: セーブパスが本番用のままです! ({SAVE_OFFICIAL_PATH})")
        sys.exit(1)
    
    print(f"✅ パスチェック合格: 現在のセーブ先 = {SAVE_OFFICIAL_PATH}")

    # 3. 実際に保存して本番ファイルが書き換わらないか検証
    official_path = os.path.join(os.path.dirname(SAVE_OFFICIAL_PATH), "save_official.json")
    
    mtime_before = 0
    if os.path.exists(official_path):
        mtime_before = os.path.getmtime(official_path)
    
    # ダミー保存処理をシミュレート (Playerクラスなどを介して)
    # ここではパスの確実な分離を確認するため、SAVE_OFFICIAL_PATH への書き込みを試行
    with open(SAVE_OFFICIAL_PATH, "w") as f:
        f.write('{"test": "isolation"}')
    
    # 本番ファイルが更新されていないか確認
    if os.path.exists(official_path):
        mtime_after = os.path.getmtime(official_path)
        if mtime_after > mtime_before and mtime_before != 0:
            print("❌ 致命的エラー: テスト中に save_official.json が更新されました!")
            sys.exit(1)

    print("✅ 隔離テスト合格: 本番用セーブデータは保護されています。")

if __name__ == "__main__":
    test_save_isolation()
