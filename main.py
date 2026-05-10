import pygame
import os
import sys
import traceback

# プロジェクトルートをパスに追加（念のため）
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dependencies import *
from systems.session_handler import start_new_game as session_start, continue_game as session_continue, init_ui_elements
from systems.scene_handler import handle_opening, handle_title, handle_game, handle_ending
from systems.audio_manager import play_bgm

def main():
    """メインエントリーポイント"""
    try:
        # --- 初期セットアップ ---
        ui_elements = init_ui_elements(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # セーブデータに応じた初期シーン設定
        from systems.data_loader import SAVE_OFFICIAL_PATH, SAVE_SUSPEND_PATH
        has_save = os.path.exists(SAVE_OFFICIAL_PATH) or os.path.exists(SAVE_SUSPEND_PATH)
        
        # プレイヤーとダンジョンの初期化（ダミー）
        player = Player()
        dungeon = None
        
        # セッション開始用関数
        def start_new_game():
            nonlocal player, dungeon
            player, dungeon = session_start(ui_elements, game_state)
            game_state["current_scene"] = "game"

        def continue_game():
            nonlocal player, dungeon
            player, dungeon = session_continue(ui_elements, game_state, player)
            game_state["current_scene"] = "game"

        # 初期シーンとBGMの設定
        if not has_save and not game_state.get("opening_seen"):
            game_state["current_scene"] = "opening"
            play_bgm(BGM_OPENING)
        else:
            game_state["current_scene"] = "title"
            game_state["title_selected_idx"] = 0 if has_save else 1
            play_bgm(BGM_TITLE)

        # --- メインループ ---
        running = True
        last_scene = None
        
        while running:
            # 1. 共通イベント処理
            running, events = handle_events()
            if not running: break

            scene = game_state["current_scene"]
            
            # BGMの切り替え管理
            if scene != last_scene:
                if scene == "opening": play_bgm(BGM_OPENING)
                elif scene == "title":
                    play_bgm(BGM_TITLE)
                    game_state["title_auto_selected"] = False # タイトルに戻るたびにリセット
                last_scene = scene
 
            # 2. シーン別の処理
            dt = clock.tick(60) / 1000.0 # 1フレームの経過時間（秒）を計算
            
            if scene == "opening":
                from systems.resources import opening_imgs, story_data
                handle_opening(screen, events, game_state, opening_imgs, start_new_game, ui_elements, story_data)
                
            elif scene == "title":
                from systems.resources import title_bg
                from systems.data_loader import SAVE_OFFICIAL_PATH, SAVE_SUSPEND_PATH
                has_save = os.path.exists(SAVE_OFFICIAL_PATH)
                
                # セーブがある場合は、最初にタイトルに入った時だけ「つづきから(0)」に自動で合わせる
                if has_save and not game_state.get("title_auto_selected"):
                    game_state["title_selected_idx"] = 0
                    game_state["title_auto_selected"] = True
                elif not has_save:
                    game_state["title_selected_idx"] = 1
                
                handle_title(screen, events, game_state, title_bg, has_save, start_new_game, continue_game)

            elif scene == "game":
                if dungeon:
                    dungeon = handle_game(screen, events, player, dungeon, ui_elements, game_state, dt=dt)
                else:
                    # ダンジョンが未初期化の場合はタイトルに戻す
                    game_state["current_scene"] = "title"

            elif scene == "ending":
                from systems.resources import ending_imgs, story_data
                handle_ending(screen, events, game_state, ending_imgs, ui_elements, story_data)

            # 3. 画面更新
            pygame.display.flip()

    except Exception as e:
        print(f"[Fatal Error] {e}")
        traceback.print_exc()
        # クラッシュ時にすぐ閉じないように待機（任意）
        # pygame.time.wait(3000)
    
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
