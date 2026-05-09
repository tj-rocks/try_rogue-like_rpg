
import os
import sys
import pygame
from unittest.mock import MagicMock, patch

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
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

if __name__ == "__main__":
    try:
        test_death_penalty()
        test_death_debt()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
