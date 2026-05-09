
import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
screen = pygame.display.set_mode((800, 600))

from systems.session_handler import init_ui_elements, start_new_game
from systems.game_state import game_state
from systems.scene_handler import handle_game
from systems.events import active_direction_keys
from constants import KEY_MOVE_LEFT, KEY_MOVE_RIGHT, KEY_MOVE_UP, KEY_MOVE_DOWN

def test_rank_up_entrance_and_warp():
    print("--- 入会試験中のB1入場テスト開始 ---")
    
    try:
        # 1. 初期化
        ui_elements = init_ui_elements(800, 600)
        player, dungeon = start_new_game(ui_elements, game_state)
        
        # プレイヤーをランク '-' に設定
        player.guild_rank = "-"
        player.active_quests = []
        
        # ダンジョン入口(D)の座標を取得
        entrance_pos = None
        for y in range(dungeon.map_height):
            for x in range(dungeon.map_width):
                if dungeon.map_data[y][x] == 3:
                    entrance_pos = (x, y)
                    break
            if entrance_pos: break
        
        if not entrance_pos:
            print("[SKIP] ダンジョン入口が見つかりませんでした")
            return

        # 2. 入会試験クエストを受注
        print("[Step] 入会試験クエストを受注")
        player.active_quests.append({
            "id": "rank_up_F",
            "type": "delivery",
            "is_rank_up": True,
            "title": "冒険者の証の回収"
        })

        # 3. 入口に向かって移動
        player.x = (entrance_pos[0] + 1) * dungeon.tile_size
        player.y = entrance_pos[1] * dungeon.tile_size
        player.target_x = player.x
        player.target_y = player.y
        
        active_direction_keys.clear()
        active_direction_keys.append(KEY_MOVE_LEFT)
        
        print("[Step] ダンジョン入口へ移動")
        # 数フレーム回して重なる
        for _ in range(20):
            dungeon = handle_game(screen, [], player, dungeon, ui_elements, game_state)
            
        # 4. 確認ダイアログの検証
        assert ui_elements["confirm_dialog"].is_active, "確認ダイアログが表示されていません"
        print(f"ダイアログ表示OK: {ui_elements['confirm_dialog'].text}")

        # 5. 「はい」を選択してワープ
        print("[Step] ダイアログで『はい』を選択")
        ui_elements["confirm_dialog"].on_yes()
        ui_elements["confirm_dialog"].is_active = False
        
        # ワープ後の更新
        for _ in range(5):
            dungeon = handle_game(screen, [], player, dungeon, ui_elements, game_state)
            
        # 6. 結果検証
        print(f"移動後の階層: B{dungeon.current_floor}F")
        assert dungeon.current_floor == 1, f"B1Fへの移動に失敗しました (Current: {dungeon.current_floor})"
        
        print("[OK] 入会試験中のB1入場テスト合格！")
        
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    test_rank_up_entrance_and_warp()
    pygame.quit()
