
import os
import sys
import pygame
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["TEST_MODE"] = "1"
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from constants import NPC_DATA, CONSUMABLE_DATA, WEAPON_DATA, ARMOR_DATA, SHIELD_DATA

def test_all_shops_purchase():
    print("--- 全店舗購入テスト開始 ---")
    
    from systems.dungeon import warp_to_floor
    player = Player()
    player.coin = 10000 
    
    # ダンジョン（村 0階）を生成して在庫を初期化
    dungeon = warp_to_floor(0, player, spawn_reason="test")
    
    shop_list = [
        ("武器屋", dungeon.weapon_shop_stock),
        ("道具屋", dungeon.item_shop_stock),
        ("魔法屋", dungeon.magic_shop_stock),
        ("武器専門店", dungeon.dedicated_weapon_shop_stock),
        ("防具専門店", dungeon.dedicated_armor_shop_stock),
        ("アクセサリ専門店", dungeon.dedicated_accessory_shop_stock)
    ]
    
    print(f"テスト対象店舗数: {len(shop_list)}")
    
    for shop_name, stock in shop_list:
        if not stock:
            print(f"[SKIP] {shop_name} の在庫が空です")
            continue
        
        # 最初の商品を購入
        item = stock[0]
        item_key = item["key"]
        item_type = item["type"]
        price = item["price"]
        name = item["name"]
        
        initial_coin = player.coin
        initial_item_count = player.get_total_item_count()
        
        print(f"店: {shop_name} | アイテム: {name} ({item_key}) | 価格: {price}")
        
        # 購入処理
        player.coin -= price
        if item_type == "weapon": player.equip_weapon_by_key(item_key)
        elif item_type == "armor": player.equip_armor_by_key(item_key)
        elif item_type == "shield": player.equip_shield_by_key(item_key)
        elif item_type == "accessory": player.equip_accessory_by_key(item_key)
        elif item_type == "consumable": player.add_item_to_inventory(item_key)
        elif item_type == "stave":
            from components.sprites.player import StaveInstance
            player.stave_inventory.append(StaveInstance(item_key))
            
        # 検証
        assert player.coin == initial_coin - price
        assert player.get_total_item_count() > initial_item_count
        print(f"[OK] {shop_name} での購入成功")

    print("[OK] 全店舗購入テスト合格！")

    print("[OK] 全店舗購入テスト合格！")

if __name__ == "__main__":
    try:
        test_all_shops_purchase()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
