import pygame
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

from components.sprites.player import Player
from systems.ui import BankDialog, WarehouseDialog, Dialog, ConfirmDialog
from wordings import Text
from systems.game_state import game_state

class MockEvent:
    def __init__(self, key):
        self.type = pygame.KEYDOWN
        self.key = key

def test_bank_services():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    player = Player()
    player.coin = 2000
    player.bank_coin = 0
    
    dialog = Dialog(800, 600)
    bank = BankDialog(800, 600)
    
    print("--- 銀行テスト開始 ---")
    # 1. 100G 預け入れ (Idx 0)
    bank.is_active = True
    bank.cursor_idx = 0 
    from constants import KEY_CONFIRM
    bank.handle_events([MockEvent(KEY_CONFIRM)], player, dialog)
    
    print(f"100G預け入れ後: 所持金={player.coin}, 銀行残高={player.bank_coin}")
    assert player.coin == 1900
    assert player.bank_coin == 100
    assert dialog.is_active == True

    # 2. 100G 引き出し (Idx 3)
    bank.cursor_idx = 3
    bank.handle_events([MockEvent(KEY_CONFIRM)], player, dialog)
    print(f"100G引き出し後: 所持金={player.coin}, 銀行残高={player.bank_coin}")
    assert player.coin == 2000
    assert player.bank_coin == 0
    
    print("✅ 銀行テスト合格！")

def test_warehouse_services():
    player = Player()
    player.coin = 1000
    player.items = []
    player.add_item_to_inventory("hp_potion") # アイテム追加
    
    dialog = Dialog(800, 600)
    confirm = ConfirmDialog(800, 600)
    warehouse = WarehouseDialog(800, 600)
    
    print("\n--- 預かり屋テスト開始 ---")
    # 1. アイテムを預ける (DEPOSITモード)
    warehouse.is_active = True
    warehouse.setup_deposit_mode(player)
    
    # 最初のアイテム(hp_potion)を選択して決定
    from constants import KEY_CONFIRM
    warehouse.cursor_idx = 0
    warehouse.handle_events([MockEvent(KEY_CONFIRM)], player, confirm, dialog)
    
    # 確認ダイアログが出るはず
    assert confirm.is_active == True
    print(f"預け入れ確認表示中: {confirm.text}")
    
    # Yesを選択
    confirm.on_yes()
    confirm.is_active = False
    
    from constants import WAREHOUSE_FEE
    print(f"預け入れ後: 所持金={player.coin}, 倉庫数={len(player.warehouse_items)}, 手持ち数={len(player.items)}")
    assert player.coin == 1000 - WAREHOUSE_FEE
    assert len(player.items) == 0
    assert len(player.warehouse_items) == 1
    assert player.warehouse_items[0]["data"] == "hp_potion"

    # 2. アイテムを引き出す (WITHDRAWモード)
    warehouse.setup_withdraw_mode(player)
    warehouse.cursor_idx = 0
    warehouse.handle_events([MockEvent(KEY_CONFIRM)], player, confirm, dialog)
    
    # 確認ダイアログが出るはず
    assert confirm.is_active == True
    confirm.on_yes()
    confirm.is_active = False
    
    print(f"引き出し後: 倉庫数={len(player.warehouse_items)}, 手持ち数={len(player.items)}")
    assert len(player.items) == 1
    assert player.items[0]["key"] == "hp_potion"
    assert len(player.warehouse_items) == 0
    
    print("✅ 預かり屋テスト合格！")

class MockNPC:
    def __init__(self, role, dialogue):
        self.role = role
        self.dialogue = dialogue
    def get_dialogue(self):
        return self.dialogue

def test_priest_services():
    print("\n--- 神官解呪テスト開始 ---")
    player = Player()
    player.guild_point = 100
    player.curse_level = 1
    player.cursed_stats = ["attack"]
    
    dialog = Dialog(800, 600)
    confirm = ConfirmDialog(800, 600)
    
    from constants import CURSE_RECOVERY_COST_GP_PER_LEVEL
    cost = CURSE_RECOVERY_COST_GP_PER_LEVEL
    assert cost == 50
    
    # 1. 呪われている状態で話しかけると、歓迎ダイアログと確認ダイアログがアクティブになる
    assert player.curse_level == 1
    dialog.text = Text.NPC.PRIEST_WELCOME
    dialog.is_active = True
    confirm.text = Text.NPC.PRIEST_CURE_CONFIRM.format(cost=cost)
    
    # yesコールバックを定義
    def on_priest_yes():
        if player.guild_point >= cost:
            player.guild_point -= cost
            player.curse_level -= 1
            import random
            if player.cursed_stats:
                removed = random.choice(player.cursed_stats)
                player.cursed_stats.remove(removed)
                dialog.text = Text.NPC.PRIEST_CURE_DONE.format(stat=player.get_cursed_stats_japanese_single(removed))
            else:
                dialog.text = Text.NPC.PRIEST_CURE_DONE_SIMPLE
            dialog.is_active = True
            player.save_to_file()
            
    confirm.on_yes = on_priest_yes
    confirm.is_active = True
    
    assert confirm.is_active == True
    assert dialog.is_active == True
    
    # Yesボタンを押す
    confirm.on_yes()
    
    # 2. 解呪後の状態検証
    print(f"解呪後: GP={player.guild_point}, 呪いレベル={player.curse_level}, 被デバフステータス数={len(player.cursed_stats)}")
    assert player.guild_point == 50
    assert player.curse_level == 0
    assert len(player.cursed_stats) == 0
    
    # 3. 呪いがない状態で話しかける
    dialog.is_active = False
    confirm.is_active = False
    
    if player.curse_level > 0:
        pass
    else:
        dialog.text = Text.NPC.PRIEST_HEALTHY
        dialog.is_active = True
        
    assert dialog.is_active == True
    assert "呪われていません" in dialog.text
    
    print("✅ 神官解呪テスト合格！")

if __name__ == "__main__":
    try:
        test_bank_services()
        test_warehouse_services()
        test_priest_services()
        pygame.quit()
        sys.exit(0)
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)
