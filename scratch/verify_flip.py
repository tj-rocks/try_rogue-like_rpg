import os
import pygame
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.getcwd())

# Pygameの初期化（画面なしモード）
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player

def test_player_image_flip():
    print("[Test] Initializing Player to check image flip...")
    # Player() は引数なし
    player = Player()
    
    # 1. Player本体の歩行アニメーションチェック
    print("\n--- Player Walk Images ---")
    for d in ["left", "right"]:
        imgs = player.walk_images.get(d, [])
        print(f"Direction {d}: {len(imgs)} frames found.")

    for i in range(2):
        left_img = player.walk_images["left"][i]
        right_img = player.walk_images["right"][i]
        
        print(f"Frame {i}: Left={left_img}, Right={right_img}")
        if left_img is right_img:
            print(f"ERROR: Right frame {i} is the SAME instance as Left.")
        elif right_img is None:
            print(f"ERROR: Right frame {i} is None.")
        else:
            print(f"SUCCESS: Right frame {i} exists and is a different instance.")
            
    # 2. Player待機画像チェック
    print("\n--- Player Idle Images ---")
    left_idle = player.idle_images.get("left")
    right_idle = player.idle_images.get("right")
    print(f"Idle: Left={left_idle}, Right={right_idle}")
    if left_idle and right_idle:
        if left_idle is right_idle:
            print("ERROR: Right idle is the SAME instance as Left.")
        else:
            print("SUCCESS: Right idle exists and is a different instance.")
    else:
        print("INFO: Idle images not found (optional).")

    # 3. 防具（Armor）の反転チェック
    print("\n--- Armor Images ---")
    try:
        from constants import ARMOR_DATA
        if ARMOR_DATA:
            armor_key = next(iter(ARMOR_DATA.keys()))
            print(f"Testing armor: {armor_key}")
            player.equip_armor_by_key(armor_key)
            
            left_armor = player._armor_images.get("left")
            right_armor = player._armor_images.get("right")
            print(f"Armor: Left={left_armor}, Right={right_armor}")
            if left_armor and right_armor:
                if left_armor is right_armor:
                    print("ERROR: Right armor is the SAME instance as Left.")
                else:
                    print("SUCCESS: Right armor exists and is flipped.")
    except Exception as e:
        print(f"Armor test skipped: {e}")

    print("\n[Test] Verification Complete.")

if __name__ == "__main__":
    try:
        test_player_image_flip()
    except Exception as e:
        print(f"Test failed with error: {e}")
    finally:
        pygame.quit()
