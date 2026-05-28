import pygame
import os

_current_bgm_path = None

def play_bgm(file_path, loop=-1, fade_ms=1000):
    """
    BGMを再生する。
    同じ曲が既に流れている場合は何もしない。
    """
    global _current_bgm_path
    
    if not os.path.exists(file_path):
        print(f"[Audio] BGM file not found: {file_path}")
        return

    if _current_bgm_path == file_path and pygame.mixer.music.get_busy():
        return

    try:
        # fadeout() は非同期で停止タイマーをセットするため、
        # 直後にload()やplay()を呼ぶと、新しい曲がフェードアウトタイマーによって停止されてしまう問題(バグ)がある。
        # 曲を即座に切り替える際は stop() を使って確実に停止させる。
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play(loop, fade_ms=fade_ms)
        _current_bgm_path = file_path
    except Exception as e:
        print(f"[Audio] Error playing BGM: {e}")

def stop_bgm(fade_ms=1000):
    """BGMを停止する"""
    global _current_bgm_path
    pygame.mixer.music.fadeout(fade_ms)
    _current_bgm_path = None

def play_sfx(path):
    """SEを再生する"""
    from systems.sound_handler import sound_manager
    sound_manager.play_sfx(path)
