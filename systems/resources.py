
import pygame
import os
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, GAME_TITLE, get_display_flags

# pygame全体を初期化（FontやDisplayの準備に必要）
pygame.init()

# --- 画面（Display）の設定 ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), get_display_flags())
pygame.display.set_caption(GAME_TITLE)

# --- フォントの設定 ---
from constants import UI_SETTINGS
_f_cfg = UI_SETTINGS.get("font", {})
_f_path = _f_cfg.get("path", "components/fonts/font.ttf")
_f_sizes = _f_cfg.get("size", {"small": 22, "medium": 32, "large": 48})

def load_font(size, bold=False):
    if os.path.exists(_f_path):
        f = pygame.font.Font(_f_path, size)
    else:
        f = pygame.font.SysFont(None, size)
    if bold:
        f.set_bold(True)
    return f

# よく使うサイズのフォントを事前に読み込んでおく
font_small = load_font(_f_sizes.get("small", 22))   # ステータスバー用
font_small_bold = load_font(_f_sizes.get("small", 22), bold=True) 
font_medium = load_font(_f_sizes.get("medium", 32))  # メイン・ダイアログ用
font_small_medium = load_font(26)                    # ギルドメニューなど用（少し小さめ）
font_large = load_font(_f_sizes.get("large", 48))   # タイトル・目立つ用

# UI要素別の専用サイズがあれば読み込む
font_dialog = load_font(_f_cfg.get("dialog", _f_sizes.get("medium", 32)))
font_menu = load_font(_f_cfg.get("menu", _f_sizes.get("medium", 32)))
font_hud = load_font(_f_cfg.get("hud", _f_sizes.get("small", 22)))

# --- 時計（Clock）の設定 ---
clock = pygame.time.Clock()

# --- 画像リソースの読み込み用ヘルパー ---
_image_cache = {}
def load_image(path):
    if not path: return None
    if path in _image_cache: return _image_cache[path]
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            _image_cache[path] = img
            return img
        except Exception as e:
            print(f"[\033[91mERROR\033[0m] Failed to load image: {path} - {e}")
            return None
    print(f"[\033[93mWARNING\033[0m] Image not found: {path}")
    return None

def load_scale_img(path, w, h):
    img = load_image(path)
    if img:
        return pygame.transform.smoothscale(img, (w, h))
    return None

def scale_image_aspect(img, max_w, max_h):
    if not img: return None
    w, h = img.get_size()
    ratio = min(max_w / w, max_h / h)
    return pygame.transform.smoothscale(img, (int(w * ratio), int(h * ratio)))

# --- ゲーム共通リソースの読み込み ---
from systems.data_loader import get_story_data
story_data = get_story_data()

title_bg = load_scale_img("components/pictures/ui/title_background.png", SCREEN_WIDTH, SCREEN_HEIGHT)
opening_imgs = [
    load_scale_img(f"components/pictures/opening/opening_{i}.png", SCREEN_WIDTH, SCREEN_HEIGHT)
    for i in range(1, 8) # 7ページ構成に対応
]
ending_imgs = [
    load_scale_img(f"components/pictures/ending/ending_{i}.png", SCREEN_WIDTH, SCREEN_HEIGHT)
    for i in range(1, 4)
]

def get_story_ending_images(story=None, route="core"):
    story = story or story_data
    default_imgs = ending_imgs
    if not story or "ending" not in story:
        return default_imgs

    ending_story = story.get("ending", {})
    route_story = ending_story.get(route) if isinstance(ending_story, dict) else None
    if not isinstance(route_story, dict):
        return default_imgs

    images = []
    for idx in range(1, 4):
        page_data = route_story.get(idx) or route_story.get(str(idx)) or {}
        image_path = page_data.get("image")
        img = load_scale_img(image_path, SCREEN_WIDTH, SCREEN_HEIGHT) if image_path else None
        images.append(img if img else (default_imgs[idx - 1] if idx - 1 < len(default_imgs) else None))
    return images
