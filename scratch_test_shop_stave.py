import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from components.sprites.player import Player, StaveInstance
from systems.ui import ShopDialog

class DummyDialog:
    def __init__(self):
        self.text = ""
        self.is_active = False

class DummyConfirmDialog:
    def __init__(self):
        self.text = ""
        self.is_active = False
        self.on_yes = None

def main():
    player = Player()
    player.x = 0
    player.y = 0
    player.coin = 10000
    
    # Fill consumable inventory to 11
    for i in range(11):
        player.add_item_to_inventory("hp_potion", 1)
        
    # Fill stave inventory to 9
    for i in range(9):
        player.add_stave_to_inventory("fire_stave", 5)
        
    print(f"Initial State: Consumables={player.get_item_count()}, Staves={player.get_stave_count()}, Total={player.get_total_item_count()}")
    
    shop = ShopDialog(800, 600)
    stock = [{"key": "fire_stave", "type": "stave", "name": "Fire Stave", "price": 100, "count": 5}]
    shop.open_shop("Test Shop", stock)
    shop.cursor_idx = 0
    
    dialog = DummyDialog()
    confirm_dialog = DummyConfirmDialog()
    
    # 1. Try to buy 1st stave (Should succeed since staves=9 < 10)
    print("\n--- Try to buy 10th Stave ---")
    shop.execute_transaction(player, dialog, confirm_dialog, None)
    if confirm_dialog.is_active:
        print(f"Shop asked for confirm: {confirm_dialog.text}")
        confirm_dialog.on_yes() # Execute purchase
        print(f"Purchase successful! Staves={player.get_stave_count()}, Total={player.get_total_item_count()}")
    else:
        print(f"Purchase failed! Dialog text: {dialog.text}")

    # Reset dialogs
    dialog.is_active = False
    confirm_dialog.is_active = False
    
    # 2. Try to buy 2nd stave (Should fail since staves=10 = MAX)
    print("\n--- Try to buy 11th Stave ---")
    shop.execute_transaction(player, dialog, confirm_dialog, None)
    if confirm_dialog.is_active:
        print(f"Shop asked for confirm: {confirm_dialog.text}")
        confirm_dialog.on_yes()
    else:
        print(f"Purchase failed as expected! Dialog text: {dialog.text}")

if __name__ == "__main__":
    main()
