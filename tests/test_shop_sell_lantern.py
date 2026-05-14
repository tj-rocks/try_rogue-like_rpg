import os
import sys
import pygame

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["TEST_MODE"] = "1"
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player, EquipInstance
from systems.ui import ShopDialog, Dialog, ConfirmDialog

def test_shop_sell_lantern():
    print("--- カンテラ売却テスト開始 ---")
    
    player = Player()
    
    # プレイヤーにカンテラを持たせる
    lantern_inst = EquipInstance("lantern", "basic")
    player.lantern_inventory.append(lantern_inst)
    
    initial_coin = player.coin
    
    # ショップダイアログの準備
    shop = ShopDialog(800, 600)
    shop.open_shop("テストショップ", [])
    dialog = Dialog(800, 600)
    confirm_dialog = ConfirmDialog(800, 600)
    
    # SELLモードに切り替え
    shop.setup_sell_mode(player)
    
    # リストにカンテラが含まれているか確認
    # items は (id, type, name, price, count, key) のタプル
    found_lantern = False
    lantern_sell_price = 0
    lantern_iid = lantern_inst.iid
    
    for item in shop.items:
        if item[1] == "lantern_inst" and item[0] == lantern_iid:
            found_lantern = True
            lantern_sell_price = item[3]
            break
            
    assert found_lantern, "売却リストにカンテラが表示されていません！"
    print(f"[OK] 売却リストにカンテラが存在することを確認 (売値: {lantern_sell_price} G)")
    
    # カンテラを選択して売却イベントを発火させる
    # shop.items のインデックスを検索
    target_idx = next(i for i, item in enumerate(shop.items) if item[0] == lantern_iid)
    shop.cursor_idx = target_idx
    
    # KEY_CONFIRMイベントを送信
    from constants import KEY_CONFIRM
    events = [pygame.event.Event(pygame.KEYDOWN, {"key": KEY_CONFIRM})]
    
    shop.handle_events(events, player, dialog, confirm_dialog)
    
    # confirm_dialog がアクティブになり、do_sell() コールバックが登録されたはず
    assert confirm_dialog.is_active, "確認ダイアログが表示されていません！"
    
    # YESを選択して売却を実行
    confirm_dialog.on_yes()
    
    # 検証：所持金が増え、カンテラがインベントリから消えていること
    assert player.coin == initial_coin + lantern_sell_price, "売却代金が所持金に反映されていません！"
    assert len(player.lantern_inventory) == 0, "インベントリからカンテラが削除されていません！"
    
    print("[OK] カンテラの売却・所持金増加・インベントリ削除を確認")
    print("--- テスト合格 ---")

if __name__ == "__main__":
    try:
        test_shop_sell_lantern()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
