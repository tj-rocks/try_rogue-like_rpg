import pygame
import os

class SoundManager:
    """
    SFX (効果音) と BGM (背景音楽) の再生を管理するシングルトンクラス。
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SoundManager, cls).__new__(cls)
            cls._instance.init_mixer()
        return cls._instance

    def init_mixer(self):
        """pygame.mixer の初期化とキャッシュ用辞書の準備"""
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        self.sfx_cache = {}
        self.current_bgm = None
        self.bgm_volume = 0.5
        self.sfx_volume = 0.7

    def play_sfx(self, path):
        """SEを再生する（重複再生可能、キャッシュ機能付き）"""
        if not path:
            return

        if path not in self.sfx_cache:
            if os.path.exists(path):
                try:
                    self.sfx_cache[path] = pygame.mixer.Sound(path)
                except Exception as e:
                    print(f"[SoundManager] Error loading SFX {path}: {e}")
                    return
            else:
                # ファイルが見つからない場合はダミーを登録（何度も警告を出さないため）
                self.sfx_cache[path] = None
                print(f"[SoundManager] SFX not found: {path}")
                return

        sound = self.sfx_cache[path]
        if sound:
            sound.set_volume(self.sfx_volume)
            sound.play()

    def play_bgm(self, path, loop=-1):
        """BGMを再生する（既に同じ曲が流れている場合は何もしない）"""
        if not path:
            pygame.mixer.music.stop()
            self.current_bgm = None
            return

        if self.current_bgm == path:
            return

        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self.bgm_volume)
                pygame.mixer.music.play(loop)
                self.current_bgm = path
            except Exception as e:
                print(f"[SoundManager] Error playing BGM {path}: {e}")
        else:
            print(f"[SoundManager] BGM not found: {path}")
            pygame.mixer.music.stop()
            self.current_bgm = None

    def stop_bgm(self):
        pygame.mixer.music.stop()
        self.current_bgm = None

    def set_bgm_volume(self, volume):
        self.bgm_volume = volume
        pygame.mixer.music.set_volume(volume)

    def set_sfx_volume(self, volume):
        self.sfx_volume = volume
        for sound in self.sfx_cache.values():
            if sound:
                sound.set_volume(volume)

# グローバルにアクセス可能なインスタンス
sound_manager = SoundManager()
