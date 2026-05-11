
import os
import sys
import pygame
from unittest.mock import MagicMock, patch

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["TEST_MODE"] = "1"
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from systems.death_handler import handle_death_sequence
from constants import DOCTOR_FEE

def test_death_penalty():
    print("--- 死亡ペナルティテスト開始 ---")
    
    player = Player()
    player.coin = 1000
    player.bank_coin = 500
    player.hp = 0
    player.is_dead = True
    
    # 装備を持たせる
    player.equip_weapon_by_key("bronze_sword")
    player.equip_armor_by_key("leather_armor")
    
    # モックの準備
    dungeon = MagicMock()
    dungeon.tile_size = 64
    dialog = MagicMock()
    dialog.is_active = False
    game_state = {"death_sequence_step": 3, "death_timer": 1} # ステップ3(ペナルティ適用直前)から開始
    
    # warp_to_floor をモックして副作用（ファイルのロード等）を防ぐ
    with patch("systems.dungeon.warp_to_floor") as mock_warp:
        with patch("components.sprites.player.Player.save_to_file"): # セーブもスキップ
            handle_death_sequence(player, dungeon, dialog, game_state)
    
    # 検証: 所持金
    # 1. 元 1000 -> 半分で 500
    # 2. 治療費 (DOCTOR_FEE) が引かれる
    expected_coin = 500 - DOCTOR_FEE
    print(f"所持金検証: 期待値 {expected_coin}, 実際 {player.coin}")
    assert player.coin == expected_coin
    
    # 検証: 装備ロス
    print(f"装備検証: weapon_inventory={len(player.weapon_inventory)}, equipped_weapon={player.equipped_weapon}")
    # 死亡時に初期装備（wooden_stick）が与えられるので、数は1のはず
    assert len(player.weapon_inventory) == 1
    assert player.weapon_inventory[0].key == "wooden_stick"
    assert len(player.armor_inventory) == 0
    
    # 検証: 復活
    assert player.hp == player.max_hp
    assert player.is_dead == False
    
    print("[OK] 死亡ペナルティテスト合格！")

def test_death_debt():
    print("--- 死亡時借金テスト開始 ---")
    
    player = Player()
    player.coin = 10 # 治療費に足りない
    player.bank_coin = 0
    player.hp = 0
    player.is_dead = True
    
    dungeon = MagicMock()
    dialog = MagicMock()
    game_state = {"death_sequence_step": 3, "death_timer": 1}
    
    # warp_to_floor をモック
    with patch("systems.dungeon.warp_to_floor"):
        with patch("components.sprites.player.Player.save_to_file"):
            handle_death_sequence(player, dungeon, dialog, game_state)
            
    # 検証: 借金 (10 // 2 = 5. 5 - DOCTOR_FEE = 負の値)
    # 現在 DOCTOR_FEE = 20 なので、 5 - 20 = -15
    print(f"借金検証: 実際 {player.coin}")
    assert player.coin < 0
    print("[OK] 死亡時借金テスト合格！")

def test_respawn_position():
    print("--- 復活位置検証テスト開始 ---")
    from systems.dungeon import Dungeon
    
    player = Player()
    # 0階（村）のダミーダンジョン
    dungeon = Dungeon(level=0, player=player)
    
    # 医者の位置を強制設定（通常はマップ読み込み時に設定される）
    dungeon.clinic_pos = (10, 20)
    ts = dungeon.tile_size
    
    # 死亡フラグを立ててスポーン位置設定を呼び出す
    # spawn_reason="continue" はセーブデータからの復旧時などを想定
    dungeon.set_spawn_position(player, spawn_reason="continue", is_death=True)
    
    expected_x = (dungeon.clinic_pos[0] + 1) * ts
    expected_y = dungeon.clinic_pos[1] * ts
    
    print(f"座標検証: 期待値 ({expected_x}, {expected_y}), 実際 ({player.x}, {player.y})")
    assert player.x == expected_x
    assert player.y == expected_y
    
    print("[OK] 復活位置検証テスト合格！")

def test_poison_death_revival():
    print("--- 毒状態での死亡・クリニック復活テスト開始 ---")
    
    from systems.dungeon import Dungeon
    player = Player()
    player.hp = 0
    player.is_dead = True
    player.condition = "poison"
    player.status_timer = 10
    
    dungeon = Dungeon(level=0, player=player)
    # クリニックの位置を設定
    dungeon.clinic_pos = (10, 20)
    
    dialog = MagicMock()
    game_state = {"death_sequence_step": 3, "death_timer": 1}
    
    # patchを使って実際にwarp_to_floorが呼ばれた際の処理をシミュレート
    with patch("systems.dungeon.warp_to_floor") as mock_warp:
        # warp_to_floor(0, ...) が呼ばれたら、実際に set_spawn_position を実行するように設定
        def side_effect(floor, p, **kwargs):
            if floor == 0:
                dungeon.set_spawn_position(p, spawn_reason="continue", is_death=True)
            return dungeon
        mock_warp.side_effect = side_effect
        
        with patch("components.sprites.player.Player.save_to_file"):
            handle_death_sequence(player, dungeon, dialog, game_state)
    
    # 1. 座標検証 (医者の横 (11, 20) になっているか)
    ts = 64
    expected_x = (10 + 1) * ts
    expected_y = 20 * ts
    print(f"座標検証: 期待値 ({expected_x}, {expected_y}), 実際 ({player.x}, {player.y})")
    assert player.x == expected_x
    assert player.y == expected_y
    
    # 2. ステータス検証 (復活しているか & 毒が治っているか)
    print(f"状態検証: hp={player.hp}, condition={player.condition}")
    assert not player.is_dead
    assert player.hp == player.max_hp
    assert player.condition == "normal"
    assert player.status_timer == 0
    
    print("[OK] 毒状態での死亡・クリニック復活テスト合格！")

if __name__ == "__main__":
    try:
        test_death_penalty()
        test_death_debt()
        test_respawn_position()
        test_poison_death_revival()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
