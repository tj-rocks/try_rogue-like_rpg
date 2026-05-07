import pygame
import sys
import os
import yaml

# プロジェクトのルートをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# equipment.yml のパス
YML_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../components/data/master/equipment.yml"))

def _load_yml():
    with open(YML_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _save_yml(data):
    try:
        # コメントを維持するのは難しいが、構成を崩さないように safe_dump を使用
        with open(YML_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, indent=2)
        return True
    except Exception as e:
        print(f"YAML Save Error: {e}")
        return False

def save_category_config(mode, cat_key, pos_data):
    print(f"Saving {mode} Category: {cat_key}")
    full_data = _load_yml()
    
    cat_section = f"{mode}_CATEGORIES"
    if cat_section not in full_data:
        full_data[cat_section] = {}
    if cat_key not in full_data[cat_section]:
        full_data[cat_section][cat_key] = {}
        
    full_data[cat_section][cat_key]["position"] = pos_data
    return _save_yml(full_data)

def run_viewer():
    pygame.init()
    screen = pygame.display.set_mode((1200, 800))
    pygame.display.set_caption("Equipment Offset Viewer & Editor (YML Mode)")
    clock = pygame.time.Clock()

    # データの読み込み
    yml_data = _load_yml()
    weapon_cats = yml_data.get("WEAPON_CATEGORIES", {})
    armor_cats = yml_data.get("ARMOR_CATEGORIES", {})
    shield_cats = yml_data.get("SHIELD_CATEGORIES", {})
    
    # プレビュー用の代表アイテムを探す
    def get_preview_item(mode, cat_key):
        data_section = f"{mode}_DATA"
        items = yml_data.get(data_section, {})
        for k, v in items.items():
            if v.get("category") == cat_key:
                return k, v
        return None, None

    # プレイヤー画像の読み込み
    try:
        p_dir = os.path.join(os.path.dirname(__file__), "../components/pictures/player")
        player_imgs = {
            "down": pygame.image.load(f"{p_dir}/down_1.png").convert_alpha(),
            "up": pygame.image.load(f"{p_dir}/up_1.png").convert_alpha(),
            "left": pygame.image.load(f"{p_dir}/left_1.png").convert_alpha(),
            "right": pygame.image.load(f"{p_dir}/right_1.png").convert_alpha(),
        }
    except:
        player_imgs = {d: pygame.Surface((64, 64)) for d in ["down", "up", "left", "right"]}

    font = pygame.font.SysFont("Arial", 18)
    font_bold = pygame.font.SysFont("Arial", 22, bold=True)

    mode = "WEAPON" # WEAPON, ARMOR, SHIELD
    cat_keys = {"WEAPON": list(weapon_cats.keys()), "ARMOR": list(armor_cats.keys()), "SHIELD": list(shield_cats.keys())}
    sel_idx = {"WEAPON": 0, "ARMOR": 0, "SHIELD": 0}
    
    # 編集用の一時データ (深いコピー)
    import copy
    work_pos = {
        "WEAPON": copy.deepcopy({k: v.get("position", {}) for k, v in weapon_cats.items()}),
        "ARMOR": copy.deepcopy({k: v.get("position", {}) for k, v in armor_cats.items()}),
        "SHIELD": copy.deepcopy({k: v.get("position", {}) for k, v in shield_cats.items()}),
    }

    directions = ["down", "up", "left", "right"]
    target_dir_idx = 0
    is_attacking_preview = False
    attack_anim_timer = 0
    
    message = "TAB: Switch Mode | S: Save | Arrow: Move (Shift: x5) | Q/E/U/O: Rot"
    msg_timer = 0

    running = True
    while running:
        screen.fill((40, 40, 45))
        
        cur_cat_key = cat_keys[mode][sel_idx[mode]]
        cur_pos = work_pos[mode][cur_cat_key]
        prev_item_key, prev_item_data = get_preview_item(mode, cur_cat_key)
        
        d_str = directions[target_dir_idx]

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    mode = "ARMOR" if mode == "WEAPON" else ("SHIELD" if mode == "ARMOR" else "WEAPON")
                
                # アイテム切り替え ( , / . )
                if event.key == pygame.K_COMMA:
                    sel_idx[mode] = (sel_idx[mode] - 1) % len(cat_keys[mode])
                if event.key == pygame.K_PERIOD:
                    sel_idx[mode] = (sel_idx[mode] + 1) % len(cat_keys[mode])
                
                dir_keys = {pygame.K_DOWN: 0, pygame.K_UP: 1, pygame.K_LEFT: 2, pygame.K_RIGHT: 3}
                if event.key in dir_keys: target_dir_idx = dir_keys[event.key]
                if event.key == pygame.K_SPACE: is_attacking_preview = not is_attacking_preview
                if event.key == pygame.K_s:
                    if save_category_config(mode, cur_cat_key, cur_pos):
                        message = f"SAVED: {mode} Category '{cur_cat_key}'"
                    else:
                        message = "SAVE FAILED!"
                    msg_timer = 120

        # キー入力調整
        keys = pygame.key.get_pressed()
        shift = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        step = 5 if shift else 1
        
        if mode == "WEAPON":
            if "hand_offsets" not in cur_pos:
                cur_pos["hand_offsets"] = {"down": [[0,0],[0,0]], "up": [[0,0],[0,0]], "left": [[0,0],[0,0]], "right": [[0,0],[0,0]]}
            if "weapon_angles" not in cur_pos:
                cur_pos["weapon_angles"] = {"down": [0,0], "up": [0,0], "left": [0,0], "right": [0,0]}
            
            off = cur_pos["hand_offsets"][d_str]
            ang = cur_pos["weapon_angles"][d_str]
            if keys[pygame.K_w]: off[0][1] -= step
            if keys[pygame.K_s]: off[0][1] += step
            if keys[pygame.K_a]: off[0][0] -= step
            if keys[pygame.K_d]: off[0][0] += step
            if keys[pygame.K_i]: off[1][1] -= step
            if keys[pygame.K_k]: off[1][1] += step
            if keys[pygame.K_j]: off[1][0] -= step
            if keys[pygame.K_l]: off[1][0] += step
            if keys[pygame.K_q]: ang[0] = (ang[0] - step) % 360
            if keys[pygame.K_e]: ang[0] = (ang[0] + step) % 360
            if keys[pygame.K_u]: ang[1] = (ang[1] - step) % 360
            if keys[pygame.K_o]: ang[1] = (ang[1] + step) % 360
        else: # ARMOR or SHIELD
            if "offsets" not in cur_pos:
                cur_pos["offsets"] = {"down": [0,0], "up": [0,0], "left": [0,0], "right": [0,0]}
            off = cur_pos["offsets"][d_str]
            if keys[pygame.K_w]: off[1] -= step
            if keys[pygame.K_s]: off[1] += step
            if keys[pygame.K_a]: off[0] -= step
            if keys[pygame.K_d]: off[0] += step

        # --- 描画 ---
        preview_surf = pygame.Surface((400, 400))
        preview_surf.fill((30, 30, 30))
        center = (200, 200)
        
        # プレイヤー
        p_img = pygame.transform.scale(player_imgs[d_str], (256, 256))
        preview_surf.blit(p_img, (center[0]-128, center[1]-128))
        
        # プレビュー品
        if prev_item_key:
            try:
                scale = 4.0 # プレビュー倍率
                if mode == "WEAPON":
                    img_path = os.path.join(os.path.dirname(__file__), "..", prev_item_data["image_path"])
                    w_img = pygame.image.load(img_path).convert_alpha()
                    img_scale = weapon_cats[cur_cat_key].get("image_scale", 1.0)
                    w_img = pygame.transform.scale(w_img, (int(w_img.get_width()*scale*img_scale), int(w_img.get_height()*scale*img_scale)))
                    
                    t = 0
                    if is_attacking_preview:
                        attack_anim_timer = (attack_anim_timer + 2) % 100
                        t = attack_anim_timer / 100.0
                    
                    off = cur_pos["hand_offsets"][d_str]
                    ang = cur_pos["weapon_angles"][d_str]
                    curr_off = [off[0][0] + (off[1][0] - off[0][0]) * t, off[0][1] + (off[1][1] - off[0][1]) * t]
                    curr_ang = ang[0] + (ang[1] - ang[0]) * t
                    
                    rot_img = pygame.transform.rotate(w_img, curr_ang)
                    rect = rot_img.get_rect(center=(center[0] + curr_off[0]*scale, center[1] + curr_off[1]*scale))
                    preview_surf.blit(rot_img, rect)
                    
                elif mode == "ARMOR":
                    img_dir = os.path.join(os.path.dirname(__file__), "..", prev_item_data["image_dir"])
                    img_path = f"{img_dir}/{d_str}.png"
                    if not os.path.exists(img_path): img_path = f"{img_dir}/{d_str}_1.png"
                    a_img = pygame.image.load(img_path).convert_alpha()
                    a_img = pygame.transform.scale(a_img, (256, 256))
                    off = cur_pos["offsets"][d_str]
                    preview_surf.blit(a_img, (center[0]-128 + off[0]*scale, center[1]-128 + off[1]*scale))
                    
                elif mode == "SHIELD":
                    img_dir = os.path.join(os.path.dirname(__file__), "..", prev_item_data["image_dir"])
                    img_path = f"{img_dir}/{d_str}.png"
                    if not os.path.exists(img_path): img_path = f"{img_dir}/{d_str}_1.png"
                    s_img = pygame.image.load(img_path).convert_alpha()
                    img_scale = shield_cats[cur_cat_key].get("image_scale", 1.0)
                    s_img = pygame.transform.scale(s_img, (int(s_img.get_width()*scale*img_scale), int(s_img.get_height()*scale*img_scale)))
                    off = cur_pos["offsets"][d_str]
                    rect = s_img.get_rect(center=(center[0] + off[0]*scale, center[1] + off[1]*scale))
                    preview_surf.blit(s_img, rect)
            except Exception as e:
                pass

        screen.blit(preview_surf, (50, 100))
        
        # UI
        tx = 500
        screen.blit(font_bold.render(f"MODE: {mode} (TAB)", True, (255, 255, 100)), (tx, 100))
        screen.blit(font_bold.render(f"CATEGORY: {cur_cat_key}", True, (255, 255, 255)), (tx, 130))
        screen.blit(font.render(f"Preview Item: {prev_item_key}", True, (200, 200, 200)), (tx, 160))
        
        # カテゴリ一覧
        ry = 220
        screen.blit(font_bold.render("Categories:", True, (200, 255, 200)), (tx, ry))
        for i, k in enumerate(cat_keys[mode]):
            color = (255, 255, 0) if i == sel_idx[mode] else (150, 150, 150)
            screen.blit(font.render(f"{k}", True, color), (tx, ry + 30 + i * 25))
            
        # 操作説明
        screen.blit(font.render(message, True, (255, 255, 255)), (50, 520))
        if msg_timer > 0: msg_timer -= 1
        else: message = "TAB: Mode | S: Save | , / . : Select Category | Arrow: Facing | W/A/S/D: Move"

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    run_viewer()
