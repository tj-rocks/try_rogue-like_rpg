import os
import sys
import pygame
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化（ヘッドレスモード）
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()

from components.sprites.player import Player
from components.sprites.enemy import Enemy
from systems.dungeon import Dungeon
from systems.game_state import game_state

def test_attack_turn_transition():
    print("\n[TEST] 攻撃後のターン遷移テストを開始...")
    
    # --- 1. セットアップ ---
    # ダミーのダンジョンを作成
    dungeon = MagicMock(spec=Dungeon)
    dungeon.tile_size = 64
    dungeon.map_width = 10
    dungeon.map_height = 10
    dungeon.current_floor = 1 # フロア0以外にする
    # 床(1)で埋める
    dungeon.map_data = [[1 for _ in range(10)] for _ in range(10)]
    dungeon.enemies = []
    dungeon.dropped_items = []
    dungeon.traps = []
    dungeon.npcs = []
    
    # プレイヤー作成
    player = Player()
    player.x = 5 * 64
    player.y = 5 * 64
    player.facing = "right"
    
    # 敵作成 (6, 5) - 隣接
    enemy = Enemy(6 * 64, 5 * 64, "slime", player=player)
    enemy.stupidity = 0 # 確実に攻撃させる
    dungeon.enemies.append(enemy)
    
    # 初期状態の確認
    game_state["turn_state"] = "player"
    player.is_attacking = False
    player.enemy_turn_pending = False
    
    print(f"初期状態: turn_state={game_state['turn_state']}, player.is_attacking={player.is_attacking}")
    
    # --- 2. プレイヤーの攻撃実行 ---
    # KEY_ATTACK イベントをシミュレート
    from constants import KEY_ATTACK
    event = pygame.event.Event(pygame.KEYDOWN, {"key": KEY_ATTACK})
    player.operate(dungeon, dialog=MagicMock(), events=[event])
    
    print(f"攻撃開始後: is_attacking={player.is_attacking}, enemy_turn_pending={player.enemy_turn_pending}")
    
    assert player.is_attacking == True, "プレイヤーが攻撃状態になっていません"
    assert player.enemy_turn_pending == True, "enemy_turn_pending が True になっていません"
    
    # --- 3. アニメーションの進行（更新） ---
    # 攻撃アニメーションが終わるまで update を回す
    from constants import ATTACK_ANIMATION_FRAMES
    # 複数フレーム回して、is_attacking が False になるのを待つ
    for i in range(ATTACK_ANIMATION_FRAMES + 10):
        # update 内で is_paused() をチェックしているので、モックのダイアログは非アクティブにしておく
        dialog_mock = MagicMock()
        dialog_mock.is_active = False 
        player.update(dungeon, dialog=dialog_mock, events=[])
        if not player.is_attacking and game_state["turn_state"] == "enemies":
            break
        
    print(f"アニメーション終了後: is_attacking={player.is_attacking}, turn_state={game_state['turn_state']}")
    
    # --- 4. 検証 ---
    assert player.is_attacking == False, "攻撃アニメーションが終了していません"
    assert game_state["turn_state"] == "enemies", "ターンが敵（enemies）に切り替わっていません"
    assert player.enemy_turn_pending == False, "enemy_turn_pending が False にリセットされていません"
    
    print("[SUCCESS] 攻撃後のターン遷移が正常に確認されました。")

if __name__ == "__main__":
    try:
        test_attack_turn_transition()
        print("\nALL TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
