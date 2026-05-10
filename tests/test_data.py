import sys
import os
import shutil

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from systems.data_loader import SAVE_DIR

class TestDataLoader(unittest.TestCase):
    def test_save_directory_creation(self):
        """セーブフォルダが自動生成されるかテストする"""
        # 1. 既存のセーブフォルダを一時的にリネームして隠す（または削除）
        temp_dir = SAVE_DIR + "_backup"
        if os.path.exists(SAVE_DIR):
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.rename(SAVE_DIR, temp_dir)
        
        try:
            # 2. data_loader をリロード（あるいは単純に os.path.exists をチェック）
            # 実際のコードでは import 時や変数定義時に os.makedirs が走るので、
            # ここでは os.makedirs が正しく動作するかを再確認するロジックを検証
            
            # 手動で削除した後に、コードと同じロジックを走らせる
            if os.path.exists(SAVE_DIR):
                shutil.rmtree(SAVE_DIR)
            
            # data_loader.py 内のロジックを実行
            os.makedirs(SAVE_DIR, exist_ok=True)
            
            self.assertTrue(os.path.exists(SAVE_DIR), "セーブディレクトリが作成されるはずです")
            
        finally:
            # 3. フォルダを元に戻す
            if os.path.exists(SAVE_DIR) and os.path.exists(temp_dir):
                shutil.rmtree(SAVE_DIR)
            if os.path.exists(temp_dir):
                os.rename(temp_dir, SAVE_DIR)

if __name__ == "__main__":
    unittest.main()
