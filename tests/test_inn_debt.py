
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
from systems.dungeon import Dungeon
from systems.ui import handle_ui_events
from wordings import Text
from constants import INN_FEE

def test_inn_debt():
    print("--- 宿屋借金テスト ---")
    player = Player()
    player.hp = 10
    player.max_hp = 100
    player.coin = 0  # 所持金 0G
    player.x = 0
    player.y = 0
    player.facing = "right"
    
    dungeon = Dungeon(level=0, player=player)
    # 宿屋NPCを作成して配置
    inn_npc = MagicMock()
    inn_npc.name = "宿屋"
    inn_npc.x = player.x + dungeon.tile_size
    inn_npc.y = player.y
    inn_npc.width = 64
    inn_npc.height = 64
    dungeon.npcs = [inn_npc]
    
    dialog = MagicMock(); dialog.is_active = False
    confirm_dialog = MagicMock(); confirm_dialog.is_active = False
    inventory_dialog = MagicMock(); inventory_dialog.is_active = False
    status_dialog = MagicMock(); status_dialog.is_active = False
    enhance_dialog = MagicMock(); enhance_dialog.is_active = False
    item_action_dialog = MagicMock(); item_action_dialog.is_active = False
    ore_selection_dialog = MagicMock(); ore_selection_dialog.is_active = False
    
    # 決定キー(SPACE)を押して話しかけるイベントをシミュレート
    events = [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE})]
    
    # handle_ui_events を実行 (話しかける)
    handle_ui_events(events, dialog, confirm_dialog, 
                     inventory_dialog, status_dialog, enhance_dialog, item_action_dialog, ore_selection_dialog,
                     player=player, dungeon=dungeon)
    
    # 確認ダイアログが出ているはず
    assert confirm_dialog.is_active == True
    print(f"確認ダイアログ表示中: {confirm_dialog.text}")
    
    # 「はい」を選択した時のコールバックを直接実行
    confirm_dialog.on_yes()
    
    # 期待される結果:
    # 1. HPが全快していること
    assert player.hp == player.max_hp
    # 2. 所持金がマイナス（-INN_FEE）になっていること
    assert player.coin == -INN_FEE
    # 3. 借金用のメッセージが表示されていること
    assert dialog.text == Text.NPC.INN_DEBT
    assert dialog.text == "お金が足りないだって。しょうがない、今回はツケにしておいてあげるよ。"
    print(f"借金成功: 所持金 {player.coin}G")

    # --- 借金返済（売却）テスト ---
    print("--- 借金返済テスト ---")
    # テスト用の武器を追加
    weapon_inst = player.equip_weapon_by_key("old_sword")
    assert weapon_inst in player.weapon_inventory
    
    initial_debt = player.coin # -60
    sell_price = 100
    
    # 武器を売却 (削除して加算)
    player.remove_weapon_by_iid(weapon_inst.iid)
    player.coin += sell_price
    
    assert weapon_inst not in player.weapon_inventory
    # 期待される結果: -60 + 100 = 40
    assert player.coin == initial_debt + sell_price
    print(f"[OK] 借金返済テスト合格: 武器を売却後の所持金 {player.coin}G")
    
    print(f"[OK] 宿屋借金・返済テスト合格: 最終所持金 {player.coin}G, HP {player.hp}/{player.max_hp}")

if __name__ == "__main__":
    try:
        test_inn_debt()
        print("\n🎉 宿屋借金テストに合格しました！")
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
