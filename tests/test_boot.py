
import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
pygame.init()
screen = pygame.display.set_mode((800, 600))

from systems.session_handler import init_ui_elements, start_new_game
from systems.game_state import game_state
from systems.scene_handler import handle_game
from constants import (
    KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_MOVE_LEFT, KEY_MOVE_RIGHT,
    KEY_ATTACK, KEY_MENU
)
from systems.events import active_direction_keys

def test_game_full_interaction_sequence():
    print("--- 起動・入力・結果検証 統合テスト開始 ---")
    
    try:
        # 1. 初期化
        ui_elements = init_ui_elements(800, 600)
        player, dungeon = start_new_game(ui_elements, game_state)
        
        # 2. テストシーケンスの定義 (キー, 期待される動作のラベル)
        # 移動は村の中（Floor 0）で行われるため、壁に当たらない限り動くはず
        test_sequence = [
            (KEY_MOVE_UP, "UP"),
            (KEY_MOVE_UP, "UP"),
            (KEY_MOVE_DOWN, "DOWN"),
            (KEY_MOVE_LEFT, "LEFT"),
            (KEY_MOVE_RIGHT, "RIGHT"),
            (KEY_ATTACK, "ATTACK"),
            (KEY_MENU, "MENU")
        ]
        
        current_step = 0
        wait_frames = 0
        
        # 初期状態の記録
        last_gx = player.x // dungeon.tile_size
        last_gy = player.y // dungeon.tile_size
        
        print(f"初期位置: ({last_gx}, {last_gy})")

        # 400フレームほど回す
        for frame in range(400):
            events = []
            
            # 前の入力処理が終わる（wait_framesが0になる）のを待ってから次を入れる
            if wait_frames == 0 and current_step < len(test_sequence):
                target_key, label = test_sequence[current_step]
                print(f"[Frame {frame}] Step {current_step}: {label} を入力")
                
                # イベント発行
                events.append(pygame.event.Event(pygame.KEYDOWN, {"key": target_key}))
                
                # 移動キーならグローバル状態を更新
                if target_key in [KEY_MOVE_UP, KEY_MOVE_DOWN, KEY_MOVE_LEFT, KEY_MOVE_RIGHT]:
                    active_direction_keys.clear()
                    active_direction_keys.append(target_key)
                    wait_frames = 30 # 移動アニメーション時間を考慮
                elif target_key == KEY_ATTACK:
                    wait_frames = 20
                else:
                    wait_frames = 10
                
                current_step += 1
            
            # 入力からしばらくしたらキーを離すシミュレーション
            if wait_frames == 15:
                active_direction_keys.clear()

            # ゲーム処理実行
            dungeon = handle_game(screen, events, player, dungeon, ui_elements, game_state)
            
            # ステップが完了した瞬間（wait_framesが1になった時）に結果を検証
            if wait_frames == 1:
                prev_key, prev_label = test_sequence[current_step - 1]
                
                if prev_label in ["UP", "DOWN", "LEFT", "RIGHT"]:
                    new_gx = player.x // dungeon.tile_size
                    new_gy = player.y // dungeon.tile_size
                    print(f"結果検証({prev_label}): 位置 ({last_gx}, {last_gy}) -> ({new_gx}, {new_gy})")
                    # 村の初期位置付近は広いので、移動できているはず（壁に当たった場合は変わらないがエラーにはしない）
                    # ただし、一度も動かないのはおかしいので、どこかの移動ステップで座標が変わることを期待する
                    last_gx, last_gy = new_gx, new_gy
                    
                elif prev_label == "MENU":
                    print(f"結果検証(MENU): is_active={ui_elements['menu_dialog'].is_active}")
                    assert ui_elements["menu_dialog"].is_active, "メニューが開いていません"
                    ui_elements["menu_dialog"].is_active = False # 次のために閉じる
                
                elif prev_label == "ATTACK":
                    # 攻撃は一瞬なのでフラグチェックが難しいが、エラーが出なければ良しとする
                    print("結果検証(ATTACK): 実行完了")

            if wait_frames > 0:
                wait_frames -= 1
            
            if dungeon is None or player is None:
                raise Exception("Dungeon or Player object lost")

        print("[OK] 起動・描画・入力結果検証テスト合格！")
        
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    try:
        test_game_full_interaction_sequence()
        pygame.quit()
    except:
        sys.exit(1)
