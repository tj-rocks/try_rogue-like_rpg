import pygame
from constants import CONSUMABLE_DATA
from systems.magic_handler import execute_stave
from wordings import Text

def use_consumable(item_key, player):
    """
    消耗品アイテムを使用するロジック。
    """
    if item_key not in CONSUMABLE_DATA:
        return Text.Item.USE_NOTHING.format(item=item_key)

    data = CONSUMABLE_DATA[item_key]
    effect = data.get("effect")

    # 🎵 SE再生
    from systems.sound_handler import sound_manager
    sound_manager.play_sfx(data.get("sound"))

    # ---- エフェクト処理 ----
    if effect == "heal_hp":
        amount = data.get("heal_amount", 20)
        old_hp = player.hp
        player.hp = min(player.max_hp, player.hp + amount)
        recovered = player.hp - old_hp
        msg = Text.Item.RECOVER_HP.format(item=data['name'], recovered=recovered)
    elif effect == "antidote":
        player.condition = "normal"
        msg = f"{data['name']}を使用した 毒が消えた"
    elif effect == "material":
        msg = Text.Item.MATERIAL_DESC
        return msg
    elif effect == "lantern":
        # カンテラをインベントリに加えるだけにする（自動装備を廃止）
        lantern_key = data.get("lantern_key", "basic")
        inst = player.equip_lantern_by_key(lantern_key)
        if inst:
            msg = Text.Item.GET.format(name=inst.get_name())
        else:
            msg = Text.Item.USE_NOTHING.format(item=data['name'])
    elif effect == "warp_home":
        msg = f"{data['name']}を使用した 身体が光に包まれる..."
    else:
        msg = Text.Item.USE_NOTHING.format(item=data['name'])
        return msg

    # ---- インベントリから1個消費（リストから削除） ----
    player.remove_item_by_key(item_key)

    return msg

def discard_item(player, item_type, iid_or_key):
    """
    アイテムを破棄する。装備中の場合は拒否する。
    """
    # 装備中チェック
    is_equipped = False
    if item_type == "weapon" and player.equipped_weapon == iid_or_key: is_equipped = True
    if item_type == "armor" and player.equipped_armor == iid_or_key: is_equipped = True
    if item_type == "shield" and player.equipped_shield == iid_or_key: is_equipped = True
    if item_type == "lantern" and getattr(player, "equipped_lantern", None) == iid_or_key: is_equipped = True
    
    if is_equipped:
        return Text.Item.EQUIPPED_CANT_DISCARD, False

    # 削除処理
    name = "アイテム"
    if item_type == "weapon":
        inst = player._find_equip_inst(player.weapon_inventory, iid_or_key)
        if inst:
            name = inst.get_name()
            player.weapon_inventory.remove(inst)
    elif item_type == "armor":
        inst = player._find_equip_inst(player.armor_inventory, iid_or_key)
        if inst:
            name = inst.get_name()
            player.armor_inventory.remove(inst)
    elif item_type == "shield":
        inst = player._find_equip_inst(player.shield_inventory, iid_or_key)
        if inst:
            name = inst.get_name()
            player.shield_inventory.remove(inst)
    elif item_type == "lantern":
        inst = player._find_equip_inst(player.lantern_inventory, iid_or_key)
        if inst:
            name = inst.get_name()
            player.lantern_inventory.remove(inst)
    elif item_type == "stave":
        inst = player._find_stave_inst(iid_or_key)
        if inst:
            name = inst.name
            player.stave_inventory.remove(inst)
    else:
        # 消耗品
        if player.has_item(iid_or_key):
            name = CONSUMABLE_DATA.get(iid_or_key, {}).get("name", iid_or_key)
            player.remove_item_by_key(iid_or_key)
            
    return Text.Item.DISCARDED.format(name=name), True

def make_use_item_callback(player, dialog, inventory_dialog, game_state, dungeon=None, **kwargs):
    """
    インベントリでのアイテム選択（使用・装備）
    """
    def use_item(item_type, item_key_or_iid):
        # 装備中のチェック
        if item_type == "weapon" and player.equipped_weapon == item_key_or_iid: return
        if item_type == "armor" and player.equipped_armor == item_key_or_iid: return
        if item_type == "shield" and player.equipped_shield == item_key_or_iid: return
        if item_type == "lantern" and getattr(player, "equipped_lantern", None) == item_key_or_iid: return

        inventory_dialog.is_active = False
        # 最新のダンジョン情報を取得
        current_dungeon = getattr(inventory_dialog, "dungeon", dungeon)

        # ---- ランクチェック ----
        from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, CONSUMABLE_DATA, STAVE_DATA, LANTERN_DATA
        catalog = {"weapon": WEAPON_DATA, "armor": ARMOR_DATA, "shield": SHIELD_DATA, "stave": STAVE_DATA, "consumable": CONSUMABLE_DATA}
        
        # 装備品の場合は iid からキーを取得してマスタデータを参照
        item_key = None
        if item_type in ["weapon", "armor", "shield"]:
            inv_map = {"weapon": player.weapon_inventory, "armor": player.armor_inventory, "shield": player.shield_inventory}
            inst = player._find_equip_inst(inv_map[item_type], item_key_or_iid)
            if inst: item_key = inst.key
        else:
            item_key = item_key_or_iid

        item_data = catalog.get(item_type, {}).get(item_key, {})
        req_rank = item_data.get("rank") or item_data.get("min_rank") or "F"
        if current_dungeon and current_dungeon.guild_system:
            if not current_dungeon.guild_system.is_rank_at_least(player.guild_rank, req_rank):
                dialog.text = Text.Item.RANK_REQUIRED.format(rank=req_rank)
                dialog.is_active = True
                return

        if item_type == "weapon":
            player.change_weapon(item_key_or_iid)
            inst = player._find_equip_inst(player.weapon_inventory, item_key_or_iid)
            dialog.text = Text.Item.EQUIPPED.format(name=inst.get_name() if inst else "武器")
        elif item_type == "armor":
            player.change_armor(item_key_or_iid)
            inst = player._find_equip_inst(player.armor_inventory, item_key_or_iid)
            dialog.text = Text.Item.EQUIPPED.format(name=inst.get_name() if inst else "よろい")
        elif item_type == "shield":
            player.change_shield(item_key_or_iid)
            inst = player._find_equip_inst(player.shield_inventory, item_key_or_iid)
            dialog.text = Text.Item.EQUIPPED.format(name=inst.get_name() if inst else "盾")
        elif item_type == "lantern":
            player.change_lantern(item_key_or_iid)
            inst = player._find_equip_inst(player.lantern_inventory, item_key_or_iid)
            dialog.text = Text.Item.HELD.format(name=inst.get_name() if inst else "カンテラ")
        elif item_type == "stave":
            inst = player._find_stave_inst(item_key_or_iid)
            if inst:
                if inst.charges <= 0:
                    dialog.text = Text.Item.STAVE_NO_POWER
                else:
                    # 即座に効果を発動（アニメーションなし）
                    player._perform_wave(inst, current_dungeon, dialog)
                    # インベントリを閉じ、メッセージを表示
                    dialog.is_active = True
                    return
            else:
                dialog.text = Text.Item.STAVE_NOT_FOUND
        else:
            # 消耗品
            item_data = CONSUMABLE_DATA.get(item_key_or_iid, {})
            if item_data.get("effect") == "recharge":
                if not player.stave_inventory:
                    dialog.text = Text.Item.NO_STAVES
                else:
                    if kwargs.get("stave_selection_dialog"):
                        ssd = kwargs.get("stave_selection_dialog")
                        ssd.recharge_item_key = item_key_or_iid
                        ssd.update_from_player(player)
                        ssd.is_active = True
                        return
                    else:
                        dialog.text = "システムエラー: 選択ダイアログがありません"
            else:
                # 帰還の道標（warp_home）の特殊処理
                if item_data.get("effect") == "warp_home":
                    if player.is_any_quest_ready():
                        dialog.text = Text.Item.WARP_HOME_QUEST_READY
                        dialog.is_active = True
                        return
                    
                    # ワープ実行
                    from systems.dungeon import warp_to_floor
                    dialog.text = use_consumable(item_key_or_iid, player)
                    inventory_dialog.next_dungeon = warp_to_floor(0, player, spawn_reason="return")
                else:
                    dialog.text = use_consumable(item_key_or_iid, player)

        game_state["dialog_modal"] = True
        dialog.is_active = True

    return use_item

def make_recharge_callback(player, dialog, stave_selection_dialog):
    """
    杖の回数を増やす処理
    """
    def on_confirm(stave_inst, item_key):
        if not stave_inst or not item_key: return
        
        # アイテムデータから回復量を取得
        from constants import CONSUMABLE_DATA
        data = CONSUMABLE_DATA.get(item_key, {})
        amount = data.get("recharge_amount", 5)
        
        stave_inst.charges += amount
        if player.has_item(item_key):
            player.remove_item_by_key(item_key)
            
        # 🎵 SE再生
        from systems.sound_handler import sound_manager
        sound_manager.play_sfx(data.get("sound"))

        dialog.text = Text.Item.RECHARGED.format(name=stave_inst.name, amount=amount, charges=stave_inst.charges)
        dialog.is_active = True
        stave_selection_dialog.is_active = False

    return on_confirm

def make_enhance_callback(player, dialog, enhance_dialog):
    """
    鍛冶屋での強化実行処理
    """
    def on_select(item_type, iid, ore_key):
        if not iid or not ore_key: return
        
        # 選択された鉱石を1つ消費
        if not player.has_item(ore_key):
            dialog.text = Text.NPC.BLACKSMITH_NO_ITEM
            dialog.is_active = True
            enhance_dialog.is_active = False
            return
            
        if item_type == "weapon": inventory = player.weapon_inventory
        elif item_type == "armor": inventory = player.armor_inventory
        else: inventory = getattr(player, "shield_inventory", [])
        inst = player._find_equip_inst(inventory, iid)
        
        if inst:
            # 鉱石のデータから上昇値（enhance_bonus）を取得
            ore_data = CONSUMABLE_DATA.get(ore_key, {})
            bonus = ore_data.get("enhance_bonus", 1)
            
            inst.enhance += bonus
            player.remove_item_by_key(ore_key) 
            player.update_equipment_stats()
            
            up_msg = f"+{bonus}" if bonus > 0 else "変化なし"
            dialog.text = Text.Item.ENHANCED.format(name=inst.get_name())
            dialog.is_active = True
            enhance_dialog.is_active = False
            
    return on_select

def make_discard_item_callback(player, dialog, inventory_dialog, game_state):
    """
    アイテム破棄（捨てる）のコールバック生成
    """
    def discard(item_type, item_key_or_iid):
        inventory_dialog.is_active = False
        
        msg, success = discard_item(player, item_type, item_key_or_iid)
        
        dialog.text = msg
        game_state["dialog_modal"] = True
        dialog.is_active = True
        
    return discard

def unequip_item(player, item_type, iid):
    """
    装備を解除するロジック。
    """
    name = "アイテム"
    if item_type == "weapon":
        inst = player._find_equip_inst(player.weapon_inventory, iid)
        if inst:
            name = inst.get_name()
            player.unequip_weapon()
    elif item_type == "armor":
        inst = player._find_equip_inst(player.armor_inventory, iid)
        if inst:
            name = inst.get_name()
            player.unequip_armor()
    elif item_type == "shield":
        inst = player._find_equip_inst(player.shield_inventory, iid)
        if inst:
            name = inst.get_name()
            player.unequip_shield()
    elif item_type == "lantern":
        inst = player._find_equip_inst(player.lantern_inventory, iid)
        if inst:
            name = inst.get_name()
            player.unequip_lantern()
            
    return Text.Item.UNEQUIPPED.format(name=name)

def make_unequip_item_callback(player, dialog, inventory_dialog, game_state):
    """
    装備解除のコールバック生成
    """
    def unequip(item_type, iid):
        inventory_dialog.is_active = False
        msg = unequip_item(player, item_type, iid)
        dialog.text = msg
        game_state["dialog_modal"] = True
        dialog.is_active = True
        
    return unequip

