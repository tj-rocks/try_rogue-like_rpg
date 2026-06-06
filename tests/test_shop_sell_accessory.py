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

def test_shop_sell_accessory():
    print("--- アクセサリ売却テスト開始 ---")
    
    player = Player()
    
    # プレイヤーにアクセサリを持たせる
    accessory_inst = EquipInstance("accessory", "luminous_gem")
    player.accessory_inventory.append(accessory_inst)
    
    initial_coin = player.coin
    
    # ショップダイアログの準備
    shop = ShopDialog(800, 600)
    shop.open_shop("テストショップ", [])
    dialog = Dialog(800, 600)
    confirm_dialog = ConfirmDialog(800, 600)
    
    # SELLモードに切り替え
    shop.setup_sell_mode(player)
    
    # リストにアクセサリが含まれているか確認
    # items は (id, type, name, price, count, key) のタプル
    found_accessory = False
    accessory_sell_price = 0
    accessory_iid = accessory_inst.iid
    
    for item in shop.items:
        if item[1] == "accessory_inst" and item[0] == accessory_iid:
            found_accessory = True
            accessory_sell_price = item[3]
            break
            
    assert found_accessory, "売却リストにアクセサリが表示されていません！"
    print(f"[OK] 売却リストにアクセサリが存在することを確認 (売値: {accessory_sell_price} G)")
    
    # アクセサリを選択して売却イベントを発火させる
    target_idx = next(i for i, item in enumerate(shop.items) if item[0] == accessory_iid)
    shop.cursor_idx = target_idx
    
    # KEY_CONFIRMイベントを送信
    from constants import KEY_CONFIRM
    events = [pygame.event.Event(pygame.KEYDOWN, {"key": KEY_CONFIRM})]
    
    shop.handle_events(events, player, dialog, confirm_dialog)
    
    # confirm_dialog がアクティブになり、do_sell() コールバックが登録されたはず
    assert confirm_dialog.is_active, "確認ダイアログが表示されていません！"
    
    # YESを選択して売却を実行
    confirm_dialog.on_yes()
    
    # 検証：所持金が増え、アクセサリがインベントリから消えていること
    assert player.coin == initial_coin + accessory_sell_price, "売却代金が所持金に反映されていません！"
    assert len(player.accessory_inventory) == 0, "インベントリからアクセサリが削除されていません！"
    
    print("[OK] アクセサリの売却・所持金増加・インベントリ削除を確認")
    print("--- テスト合格 ---")

if __name__ == "__main__":
    try:
        test_shop_sell_accessory()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
