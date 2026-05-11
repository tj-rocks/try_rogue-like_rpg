import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化 (headless)
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from components.sprites.item import DroppedConsumable, DroppedWeapon, DroppedArmor, DroppedShield
from constants import CONSUMABLE_DATA, WEAPON_DATA, ARMOR_DATA, SHIELD_DATA

def test_no_auto_equip_scenario():
    print("--- 装備品：自動装備なし 検証テスト ---")
    
    player = Player()
    
    # 全スロットを未装備状態にする
    player.unequip_weapon()
    player.unequip_armor()
    player.unequip_shield()
    player.unequip_lantern()
    
    print(f"初期状態: Weapon={player.equipped_weapon}, Armor={player.equipped_armor}, Shield={player.equipped_shield}, Lantern={player.equipped_lantern}")

    # 1. カンテラのテスト
    lantern_data = CONSUMABLE_DATA.get("basic_lantern")
    if lantern_data:
        item_lantern = DroppedConsumable(0, 0, "basic_lantern", lantern_data)
        item_lantern.collect(player)
        
        if player.equipped_lantern is not None:
            print("❌ 失敗: カンテラが自動装備されました")
            sys.exit(1)
        else:
            print("✅ カンテラ：自動装備されませんでした")

    # 2. 武器のテスト
    weapon_key = "iron_sword"
    if weapon_key in WEAPON_DATA:
        item_weapon = DroppedWeapon(0, 0, weapon_key, WEAPON_DATA[weapon_key])
        item_weapon.collect(player)
        if player.equipped_weapon is not None:
            print("❌ 失敗: 武器が自動装備されました")
            sys.exit(1)
        else:
            print("✅ 武器：自動装備されませんでした")

    # 3. 防具のテスト
    armor_key = "leather_breastplate"
    if armor_key in ARMOR_DATA:
        item_armor = DroppedArmor(0, 0, armor_key, ARMOR_DATA[armor_key])
        item_armor.collect(player)
        if player.equipped_armor is not None:
            print("❌ 失敗: 防具が自動装備されました")
            sys.exit(1)
        else:
            print("✅ 防具：自動装備されませんでした")

    # 4. 盾のテスト
    shield_key = "wooden_round_shield"
    if shield_key in SHIELD_DATA:
        item_shield = DroppedShield(0, 0, shield_key, SHIELD_DATA[shield_key])
        item_shield.collect(player)
        if player.equipped_shield is not None:
            print("❌ 失敗: 盾が自動装備されました")
            sys.exit(1)
        else:
            print("✅ 盾：自動装備されませんでした")

    print("\n🎉 すべての自動装備なしテストに合格しました！")

if __name__ == "__main__":
    test_no_auto_equip_scenario()
