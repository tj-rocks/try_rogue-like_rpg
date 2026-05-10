import os
import sys
import pygame
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化（ヘッドレスモード）
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['TEST_MODE'] = '1' # [IMPORTANT] 本番セーブデータを保護するため
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from components.sprites.enemy import Enemy
from components.sprites.trap import Trap
from systems.dungeon import Dungeon
from systems.guild import GuildSystem
from constants import GUILD_RANKS

def setup_test_dungeon(floor):
    dungeon = Dungeon(floor)
    dungeon.map_width = 10
    dungeon.map_height = 10
    # 全て床(1)にする
    dungeon.map_data = [[1 for _ in range(10)] for _ in range(10)]
    # (5, 5) に下り階段(3)を配置
    dungeon.map_data[5][5] = 3
    dungeon.spawn_pos = (-1, -1) # ガードを無効化
    dungeon.traps = []
    return dungeon

def create_mocks():
    confirm = MagicMock()
    confirm.is_active = False
    dialog = MagicMock()
    dialog.is_active = False
    return confirm, dialog

def test_rank_minus_limits():
    print("--- [統合テスト] ランク '-' (未加入) の制限 & ワープテスト ---")
    from systems.game_state import game_state
    game_state["is_paused"] = False
    game_state["dialog_just_closed"] = False
    
    player = Player()
    player.guild_rank = "-"
    player.active_quests = []
    
    # 1. クエストなしで B0F (村) から B1F へ -> 拒否
    dungeon_b0 = setup_test_dungeon(0)
    player.x, player.y = 5 * 64, 5 * 64
    player.prev_x, player.prev_y = 4 * 64, 5 * 64
    confirm, dialog = create_mocks()
    
    dungeon_b0.check_stairs(player, confirm, dialog)
    assert dialog.is_active == True, "クエストなしでB1Fへ行こうとしたがダイアログが出ない"
    assert "入会試験" in dialog.text, f"不適切なメッセージ: {dialog.text}"
    
    # 2. rank_up_F 受注中 -> 許可 & ワープ実行
    player.active_quests = [{"id": "rank_up_F", "is_rank_up": True, "next_rank": "F"}]
    player.x, player.y = 5 * 64, 5 * 64
    player.prev_x, player.prev_y = 4 * 64, 5 * 64
    confirm, dialog = create_mocks()
    
    dungeon_b0.check_stairs(player, confirm, dialog)
    assert confirm.is_active == True, "昇格クエスト中なのにB1Fへの確認ダイアログが出ない"
    
    # ワープ実行のシミュレーション
    print("[Step] ダイアログで『はい』を選択して遷移を検証")
    confirm.on_yes()
    assert hasattr(dungeon_b0, "next_dungeon"), "next_dungeon がセットされていません"
    next_d = dungeon_b0.next_dungeon
    assert next_d.current_floor == 1, f"ワープ先が B1F ではありません (Current: {next_d.current_floor})"
    
    # 3. B10F から B11F (Fランク限界) までは行けるか
    dungeon_b10 = setup_test_dungeon(10)
    player.x, player.y = 5 * 64, 5 * 64
    confirm, dialog = create_mocks()
    dungeon_b10.check_stairs(player, confirm, dialog)
    assert confirm.is_active == True, "Fランク限界(B11F)への移動が許可されていない"
    
    # 4. B11F から B12F への進入は拒否されるか
    dungeon_b11 = setup_test_dungeon(11)
    player.x, player.y = 5 * 64, 5 * 64
    confirm, dialog = create_mocks()
    dungeon_b11.check_stairs(player, confirm, dialog)
    assert dialog.is_active == True, "Fランク制限(B11)を超えたB12Fへの進入がブロックされていない"
    print("[OK] ランク '-' の統合テスト通過")

def test_rank_f_limits():
    print("--- [統合テスト] ランク 'F' の制限 & ワープテスト ---")
    player = Player()
    player.guild_rank = "F"
    player.active_quests = []
    
    # 1. B11F から B12F へ (クエストなし) -> 拒否
    dungeon_b11 = setup_test_dungeon(11)
    player.x, player.y = 5 * 64, 5 * 64
    confirm, dialog = create_mocks()
    dungeon_b11.check_stairs(player, confirm, dialog)
    assert dialog.is_active == True, "ランクF、クエストなしで制限超過(B12)がブロックされていない"
    
    # 2. rank_up_E 受注中 -> 許可 & ワープ実行
    player.active_quests = [{"id": "rank_up_E", "is_rank_up": True, "next_rank": "E"}]
    player.x, player.y = 5 * 64, 5 * 64
    confirm, dialog = create_mocks()
    dungeon_b11.check_stairs(player, confirm, dialog)
    assert confirm.is_active == True, "昇格クエスト(E)中なのにB12Fへの進入が許可されていない"
    
    # ワープ実行のシミュレーション
    confirm.on_yes()
    next_d = dungeon_b11.next_dungeon
    assert next_d.current_floor == 12, f"ワープ先が B12F ではありません (Current: {next_d.current_floor})"
    
    print("[OK] ランク 'F' の統合テスト通過")

def test_pitfall_rank_limit():
    print("--- [統合テスト] 落とし穴(Pitfall)のランク制限テスト ---")
    from systems.game_state import game_state
    game_state["is_paused"] = False
    game_state["dialog_just_closed"] = False

    player = Player()
    player.guild_rank = "-"
    player.active_quests = []
    
    # B1F に落とし穴を設置
    dungeon_b1 = setup_test_dungeon(1)
    px, py = 5, 5
    player.x, player.y = px * 64, py * 64
    player.prev_x, player.prev_y = 4 * 64, py * 64
    
    pitfall = Trap(px, py, "pitfall")
    dungeon_b1.traps.append(pitfall)
    
    confirm, dialog = create_mocks()
    
    # 1. ランク不足での踏み込み -> 押し戻される
    dungeon_b1.check_traps(player, dialog)
    print(f"ランク不足踏み込み: dialog.is_active={dialog.is_active}, player.x={player.x//64}")
    assert dialog.is_active == True, "ランク不足で落とし穴を踏んだが警告が出ない"
    assert player.x // 64 == 4, "ランク不足で落とし穴を踏んだが押し戻されていない"
    assert player.is_falling == False, "ランク不足なのに落下状態になっている"
    
    # 2. 昇格クエスト受注中での踏み込み -> 落下開始
    player.active_quests = [{"id": "rank_up_F", "is_rank_up": True, "next_rank": "F"}]
    player.x, player.y = px * 64, py * 64 # 再び罠の上へ
    player.prev_x, player.prev_y = 4 * 64, py * 64
    confirm, dialog = create_mocks()
    
    dungeon_b1.check_traps(player, dialog)
    print(f"昇格クエスト中踏み込み: player.is_falling={player.is_falling}, trap.is_triggered={pitfall.is_triggered}")
    assert player.is_falling == True, "昇格クエスト中なのに落とし穴で落下しない"
    assert pitfall.is_triggered == True, "落とし穴が発動状態になっていない"
    
    print("[OK] 落とし穴のランク制限テスト通過")

if __name__ == "__main__":
    try:
        test_rank_minus_limits()
        test_rank_f_limits()
        test_pitfall_rank_limit()
        print("\n=== すべてのランク制限・遷移統合テストに合格しました！ ===")
    except AssertionError as e:
        print(f"\n[FAIL] テスト失敗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 予期せぬエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
