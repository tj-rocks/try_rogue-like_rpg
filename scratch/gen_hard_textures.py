import pygame
import os

# headless mode for pygame
os.environ['SDL_VIDEODRIVER'] = 'dummy'

pygame.init()
size = 60
target_dir = "/Users/tj/Desktop/2DGame/components/pictures/dungeon/hard"
os.makedirs(target_dir, exist_ok=True)

def save_tex(name, color, label, border=True):
    surf = pygame.Surface((size, size))
    surf.fill(color)
    if border:
        pygame.draw.rect(surf, (150, 150, 150), (0, 0, size, size), 1)
    
    # 簡易的な模様を追加
    if "floor" in name:
        pygame.draw.circle(surf, (60, 60, 70), (size//4, size//4), 5)
    elif "wall" in name:
        pygame.draw.line(surf, (200, 100, 100), (0, 0), (size, size), 2)
    
    pygame.image.save(surf, os.path.join(target_dir, name + ".png"))
    print(f"Saved {name}.png")

# ハードダンジョン用の色設定
C_FLOOR = (40, 40, 45)
C_WALL = (80, 30, 30)
C_CORR = (30, 30, 35)
C_NONE = (10, 10, 10)

# 基本セット
save_tex("floor", C_FLOOR, "Floor")
save_tex("floor_1", C_FLOOR, "Floor 1")
save_tex("floor_2", (45, 40, 40), "Floor 2")
save_tex("floor_3", (40, 45, 40), "Floor 3")
save_tex("floor_4", (40, 40, 50), "Floor 4")

save_tex("wall_top", (100, 40, 40), "Wall Top")
save_tex("wall_bottom", (60, 20, 20), "Wall Bottom")
save_tex("wall_side", (80, 40, 40), "Wall Side")
save_tex("wall_none", C_NONE, "Wall None")
save_tex("wall_corner", (120, 50, 50), "Pillar")

save_tex("corridor", C_CORR, "Corr V")
save_tex("corridor_corner_tr", C_CORR, "Corr Corner")

pygame.quit()
