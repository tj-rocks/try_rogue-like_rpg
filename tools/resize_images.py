import os
import pygame

# 処理対象のディレクトリ
TARGET_DIR = "systems/resize_images"
SIZE = (64, 64)

def resize_images():
    # pygameの初期化（画像処理のみなので最小限）
    pygame.display.init()
    
    if not os.path.exists(TARGET_DIR):
        print(f"Error: {TARGET_DIR} が見つかりません。")
        return

    # 対応する拡張子
    valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp')
    files = [f for f in os.listdir(TARGET_DIR) if f.lower().endswith(valid_extensions)]
    
    if not files:
        print(f"{TARGET_DIR} 内に画像ファイルが見つかりませんでした。")
        return

    print(f"{len(files)} 枚の画像を処理します...")

    for filename in files:
        path = os.path.join(TARGET_DIR, filename)
        try:
            # 画像の読み込み
            image = pygame.image.load(path)
            # リサイズ（滑らかなリサイズを試み、失敗したら標準スケーリング）
            try:
                resized_image = pygame.transform.smoothscale(image, SIZE)
            except:
                resized_image = pygame.transform.scale(image, SIZE)
                
            # 保存
            pygame.image.save(resized_image, path)
            print(f"Resized: {filename} to {SIZE[0]}x{SIZE[1]}")
        except Exception as e:
            print(f"Failed to resize {filename}: {e}")

    print("すべての処理が完了しました。")

if __name__ == "__main__":
    resize_images()
