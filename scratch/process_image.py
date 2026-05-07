from PIL import Image
import sys
import os

def make_transparent(img_path, output_path):
    img = Image.open(img_path).convert("RGBA")
    datas = img.getdata()

    new_data = []
    # 背景色（白）を透明にする
    # ピクセルアートなので、完全な白に近い色を対象にする
    for item in datas:
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)

    img.putdata(new_data)
    
    # 64x64にリサイズ（ドットがぼけないようにNEARESTを使用）
    img = img.resize((64, 64), Image.NEAREST)
    img.save(output_path)
    print(f"Saved transparent image to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 process_image.py <src> <dst>")
        sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2]
    make_transparent(src, dst)
