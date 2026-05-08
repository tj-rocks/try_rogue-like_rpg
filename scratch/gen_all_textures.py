import pygame
import os
import random

# Headless mode for pygame
os.environ['SDL_VIDEODRIVER'] = 'dummy'

pygame.init()
size = 60
# プロジェクトルートを取得して、相対パスで設定
current_dir = os.path.dirname(os.path.abspath(__file__))
base_path = os.path.join(current_dir, "../components/pictures/dungeon")

def add_noise(surf, amount=10):
    """表面にザラザラした質感を追加する"""
    for _ in range(int(size * size * (amount / 100))):
        x = random.randint(0, size - 1)
        y = random.randint(0, size - 1)
        c = surf.get_at((x, y))
        var = random.randint(-20, 20)
        new_c = (
            max(0, min(255, c[0] + var)),
            max(0, min(255, c[1] + var)),
            max(0, min(255, c[2] + var))
        )
        surf.set_at((x, y), new_c)

def save_image(surf, folder, name):
    target_dir = os.path.join(base_path, folder)
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, name + ".png")
    pygame.image.save(surf, path)
    print(f"Generated: {folder}/{name}.png")

# --- 生成関数群 ---

def gen_ice(folder):
    # Floor: 氷のタイル
    for name, var_color in [("floor", 0), ("floor_1", 20)]:
        s = pygame.Surface((size, size))
        s.fill((180 + var_color, 230, 255))
        for _ in range(5): # 氷のヒビ
            x1, y1 = random.randint(0, size), random.randint(0, size)
            x2, y2 = random.randint(0, size), random.randint(0, size)
            pygame.draw.line(s, (220, 245, 255), (x1, y1), (x2, y2), 1)
        add_noise(s, 5)
        save_image(s, folder, name)
    
    # Wall Top: 雪の積もった岩
    s = pygame.Surface((size, size))
    s.fill((100, 100, 120)) # ベースの岩
    pygame.draw.rect(s, (240, 250, 255), (0, 0, size, size//2)) # 雪
    add_noise(s, 10)
    save_image(s, folder, "wall_top")
    
    # Wall Base: 深い氷
    s = pygame.Surface((size, size))
    s.fill((50, 100, 150))
    pygame.draw.rect(s, (100, 150, 200), (0, 0, size, size), 4)
    save_image(s, folder, "wall_base")
    
    # Corridor
    s = pygame.Surface((size, size))
    s.fill((150, 200, 220))
    pygame.draw.line(s, (100, 150, 180), (size//2, 0), (size//2, size), 3)
    save_image(s, folder, "corridor")

def gen_lava(folder):
    # Floor: 黒い溶岩石
    for name in ["floor", "floor_1"]:
        s = pygame.Surface((size, size))
        s.fill((40, 30, 30))
        for _ in range(3): # 溶岩の割れ目
            pts = [(random.randint(0, size), random.randint(0, size)) for _ in range(3)]
            pygame.draw.lines(s, (200, 50, 0), False, pts, 2)
        add_noise(s, 15)
        save_image(s, folder, name)
    
    # Wall Top: 赤く光る岩
    s = pygame.Surface((size, size))
    s.fill((60, 40, 40))
    pygame.draw.rect(s, (150, 30, 0), (0, 0, size, 10))
    add_noise(s, 12)
    save_image(s, folder, "wall_top")
    
    save_image(s, folder, "wall_base") # 流用
    
    # Corridor
    s = pygame.Surface((size, size))
    s.fill((50, 20, 20))
    pygame.draw.line(s, (180, 40, 0), (size//2, 0), (size//2, size), 4)
    save_image(s, folder, "corridor")

def gen_ruins(folder):
    # Floor: 苔むした石畳
    for name in ["floor", "floor_1"]:
        s = pygame.Surface((size, size))
        s.fill((100, 105, 100))
        # 石の目地
        pygame.draw.rect(s, (70, 75, 70), (0, 0, size, size), 2)
        pygame.draw.line(s, (70, 75, 70), (size//2, 0), (size//2, size), 2)
        # 苔
        for _ in range(10):
            x, y = random.randint(0, size-5), random.randint(0, size-5)
            pygame.draw.ellipse(s, (50, 80, 40), (x, y, 10, 5))
        add_noise(s, 10)
        save_image(s, folder, name)
    
    # Wall Top
    s = pygame.Surface((size, size))
    s.fill((90, 95, 90))
    pygame.draw.rect(s, (40, 60, 30), (0, 0, size, 8)) # 上部の苔
    save_image(s, folder, "wall_top")
    save_image(s, folder, "wall_base")
    
    # Corridor
    s = pygame.Surface((size, size))
    s.fill((80, 85, 80))
    pygame.draw.line(s, (40, 60, 30), (size//2, 0), (size//2, size), 3)
    save_image(s, folder, "corridor")

def gen_castle(folder):
    # Floor: 汚れたタイル or 絨毯
    for name, col in [("floor", (80, 40, 40)), ("floor_1", (60, 60, 70))]:
        s = pygame.Surface((size, size))
        s.fill(col)
        pygame.draw.rect(s, tuple(c-20 for c in col), (0, 0, size, size), 3) # 枠線
        add_noise(s, 12)
        save_image(s, folder, name)
    
    # Wall Top: レンガ
    s = pygame.Surface((size, size))
    s.fill((100, 80, 70))
    for y in range(0, size, 20):
        pygame.draw.line(s, (60, 50, 45), (0, y), (size, y), 2)
    save_image(s, folder, "wall_top")
    save_image(s, folder, "wall_base")
    
    # Corridor
    s = pygame.Surface((size, size))
    s.fill((70, 60, 55))
    pygame.draw.line(s, (40, 35, 30), (size//2, 0), (size//2, size), 4)
    save_image(s, folder, "corridor")

def gen_shallow(folder):
    # Floor: 綺麗な明るいタイル
    for name in ["floor", "floor_1"]:
        s = pygame.Surface((size, size))
        s.fill((200, 190, 180))
        pygame.draw.rect(s, (170, 160, 150), (2, 2, size-4, size-4), 1)
        add_noise(s, 3)
        save_image(s, folder, name)
    
    s = pygame.Surface((size, size))
    s.fill((180, 170, 160))
    pygame.draw.rect(s, (140, 130, 120), (0, 0, size, 10))
    save_image(s, folder, "wall_top")
    save_image(s, folder, "wall_base")
    
    s = pygame.Surface((size, size))
    s.fill((170, 160, 150))
    pygame.draw.line(s, (130, 120, 110), (size//2, 0), (size//2, size), 2)
    save_image(s, folder, "corridor")

def gen_wood(folder):
    # Floor: 板張り
    for name in ["floor", "floor_1"]:
        s = pygame.Surface((size, size))
        s.fill((139, 90, 43))
        for x in range(0, size, 15):
            pygame.draw.line(s, (80, 50, 20), (x, 0), (x, size), 2)
        add_noise(s, 8)
        save_image(s, folder, name)
    
    s = pygame.Surface((size, size))
    s.fill((160, 110, 60))
    pygame.draw.rect(s, (100, 70, 40), (0, 0, size, 12))
    save_image(s, folder, "wall_top")
    save_image(s, folder, "wall_base")
    
    s = pygame.Surface((size, size))
    s.fill((120, 80, 40))
    pygame.draw.line(s, (70, 40, 10), (size//2, 0), (size//2, size), 4)
    save_image(s, folder, "corridor")

def gen_stone_brick(folder):
    # Floor: 石レンガ
    for name in ["floor", "floor_1"]:
        s = pygame.Surface((size, size))
        s.fill((120, 120, 125))
        pygame.draw.rect(s, (80, 80, 85), (0, 0, size, size), 2)
        pygame.draw.line(s, (80, 80, 85), (0, size//2), (size, size//2), 2)
        add_noise(s, 10)
        save_image(s, folder, name)
    
    s = pygame.Surface((size, size))
    s.fill((140, 140, 145))
    pygame.draw.rect(s, (90, 90, 95), (0, 0, size, 15))
    save_image(s, folder, "wall_top")
    save_image(s, folder, "wall_base")
    
    s = pygame.Surface((size, size))
    s.fill((110, 110, 115))
    pygame.draw.line(s, (70, 70, 75), (size//2, 0), (size//2, size), 3)
    save_image(s, folder, "corridor")

# --- 実行 ---
gen_ice("ice")
gen_lava("lava")
gen_ruins("ruins")
gen_castle("castle")
gen_shallow("shallow")
gen_wood("wood")
gen_stone_brick("stone_brick")

pygame.quit()
print("All textures generated successfully!")
