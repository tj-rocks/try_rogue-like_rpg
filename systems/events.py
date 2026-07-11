import pygame
from constants import KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_MOVE_LEFT, KEY_MOVE_RIGHT

# 押されている方向キーを順番に記憶するリスト
active_direction_keys = []

def clear_input_events():
    """ロード/セーブ突入時に入力キューと押下履歴を破棄する。"""
    pygame.event.pump()
    pygame.event.clear()
    active_direction_keys.clear()

def handle_events():
    global active_direction_keys
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            return False, events
            
        if event.type == pygame.KEYDOWN:
            if event.key in (KEY_MOVE_LEFT, KEY_MOVE_RIGHT, KEY_MOVE_UP, KEY_MOVE_DOWN):
                if event.key in active_direction_keys:
                    active_direction_keys.remove(event.key)
                active_direction_keys.append(event.key)
                
        elif event.type == pygame.KEYUP:
            if event.key in active_direction_keys:
                active_direction_keys.remove(event.key)
                
    return True, events
