import pygame
import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

# Mock pygame screen
pygame.display.set_mode((1, 1), pygame.NOFRAME)

from components.sprites.player import Player, EquipInstance
import constants

def test_equipment_offsets():
    print("[TEST] 装備品オフセット変更の検証を開始...")
    
    player = Player()
    
    # --- 1. 盾のオフセット検証 ---
    print("\n[Shield Offset Test]")
    # 盾を装備させる
    shield_inst = EquipInstance("shield", "wooden_round_shield")
    player.shield_inventory.append(shield_inst)
    player.change_shield(shield_inst.iid)
    
    # 初期座標の計算（簡易的に内部ロジックをシミュレート）
    def get_shield_draw_pos(p):
        inst = p._find_equip_inst(p.shield_inventory, p.equipped_shield)
        data = constants.SHIELD_DATA.get(inst.key, {})
        cat_data = data
        offsets = cat_data.get("position", {}).get("offsets", {}).get(p.facing, (0, 0))
        # 簡易計算（Player._draw_shield_overlay と同様）
        off_x = offsets[0]
        off_y = offsets[1]
        return off_x, off_y

    player.set_facing("down")
    ox1, oy1 = get_shield_draw_pos(player)
    print(f"初期オフセット (down): {ox1}, {oy1}")

    # マスターデータを直接書き換える
    original_offsets = constants.SHIELD_DATA["wooden_round_shield"]["position"]["offsets"]["down"]
    constants.SHIELD_DATA["wooden_round_shield"]["position"]["offsets"]["down"] = [ox1 + 10, oy1 + 20]
    
    ox2, oy2 = get_shield_draw_pos(player)
    print(f"変更後オフセット (down): {ox2}, {oy2}")
    
    assert ox2 == ox1 + 10 and oy2 == oy1 + 20, "盾のオフセットが反映されていません"
    print("✓ 盾のオフセット反映成功")

    # 元に戻す
    constants.SHIELD_DATA["wooden_round_shield"]["position"]["offsets"]["down"] = original_offsets

    # --- 2. 鎧のオフセット検証 ---
    print("\n[Armor Offset Test]")
    armor_inst = EquipInstance("armor", "adventurers_clothes")
    player.armor_inventory.append(armor_inst)
    player.change_armor(armor_inst.iid)

    def get_armor_draw_pos(p):
        inst = p._find_equip_inst(p.armor_inventory, p.equipped_armor)
        data = constants.ARMOR_DATA.get(inst.key, {})
        cat_data = data
        offsets = cat_data.get("position", {}).get("offsets", {}).get(p.facing, (0, 0))
        return offsets[0], offsets[1]

    player.set_facing("left")
    ax1, ay1 = get_armor_draw_pos(player)
    print(f"初期オフセット (left): {ax1}, {ay1}")

    constants.ARMOR_DATA["adventurers_clothes"]["position"]["offsets"]["left"] = [ax1 - 5, ay1 + 15]
    
    ax2, ay2 = get_armor_draw_pos(player)
    print(f"変更後オフセット (left): {ax2}, {ay2}")
    
    assert ax2 == ax1 - 5 and ay2 == ay1 + 15, "鎧のオフセットが反映されていません"
    print("✓ 鎧のオフセット反映成功")

    # --- 3. 武器のオフセット検証 ---
    print("\n[Weapon Offset Test]")
    player.change_weapon(player.weapon_inventory[0].iid) # 初期装備(古びた剣)
    weapon = player.weapon
    
    def get_weapon_hand_offset(w, facing):
        # Weapon.__init__ で HAND_OFFSETS が設定されている
        return w.HAND_OFFSETS.get(facing, [[0,0],[0,0]])[0] # Idle offset

    player.set_facing("right")
    wx1, wy1 = get_weapon_hand_offset(weapon, "right")
    print(f"初期武器オフセット (right): {wx1}, {wy1}")

    # 武器のカテゴリ（WEAPON_TYPES / WEAPON_CATEGORIES）を書き換える
    constants.WEAPON_DATA[weapon.key]["position"]["hand_offsets"]["right"][0] = [wx1 + 30, wy1 - 10]
    
    # 武器インスタンスを再生成して反映を確認（ゲーム内では装備時に生成される）
    new_weapon = player._get_weapon_instance(weapon.key)
    wx2, wy2 = get_weapon_hand_offset(new_weapon, "right")
    print(f"変更後武器オフセット (right): {wx2}, {wy2}")

    assert wx2 == wx1 + 30 and wy2 == wy1 - 10, "武器のオフセットが反映されていません"
    print("✓ 武器のオフセット反映成功")

    print("\n[SUCCESS] すべての装備品オフセット検証を通過しました！")

if __name__ == "__main__":
    try:
        test_equipment_offsets()
    except Exception as e:
        print(f"\n[FAIL] テスト失敗: {e}")
        sys.exit(1)
