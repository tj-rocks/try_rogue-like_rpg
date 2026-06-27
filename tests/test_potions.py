import os
import sys
import pygame

# pygame のビデオドライバをダミーに設定して、ヘッドレス環境でも動くようにする
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["TEST_MODE"] = "1"
pygame.init()
pygame.display.set_mode((1, 1))

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.sprites.player import Player, EquipInstance, StaveInstance
from systems.item_handler import use_consumable
from systems.magic_handler import execute_stave

def test_potions_and_fighter_set():
    print("--- 1. 初期化とテスト準備 ---")
    player = Player()

    from constants import CONSUMABLE_DATA
    w_data = CONSUMABLE_DATA.get("warrior_potion", {})
    w_dur = w_data.get("duration", 10)
    w_val = w_data.get("value", 5)

    p_data = CONSUMABLE_DATA.get("pilgrim_potion", {})
    p_dur = p_data.get("duration", 15)
    p_val = p_data.get("value", 2)

    s_data = CONSUMABLE_DATA.get("sage_potion", {})
    s_dur = s_data.get("duration", 15)
    s_val = s_data.get("value", 0.30)

    hp_pot_data = CONSUMABLE_DATA.get("hp_potion", {})
    hp_pot_heal = hp_pot_data.get("heal_amount", 40)

    # 持ち物の整理
    player.items = []
    player.unequip_weapon()
    player.unequip_armor()
    player.unequip_shield()

    # テスト用の秘薬をインベントリに追加
    player.add_item_to_inventory("pilgrim_potion")
    player.add_item_to_inventory("warrior_potion")
    player.add_item_to_inventory("sage_potion")

    # 初期攻撃力・初期回復ボーなスの確認
    print(f"初期攻撃力: {player.total_attack} (ベース: {player.attack})")
    print(f"初期回復ボーナス: {player.regen_bonus}")
    print(f"初期魔法(炎ダメージ)ボーナス: {player.get_magic_bonus('fire_damage')}")
    print(f"初期会心ボーナス: {player.crit_bonus}")
    print(f"初期防御無視ボーナス: {player.total_armor_penetration}")

    print("\n--- 2. 装備なしで雷霆の秘薬を使用 ---")
    msg = use_consumable("warrior_potion", player)
    print(msg)
    print(f"バフ状態: attack_buff_turns={player.attack_buff_turns}, attack_buff_val={player.attack_buff_val}")
    print(f"  attack_buff_crit={player.attack_buff_crit}, attack_buff_armor_pen={player.attack_buff_armor_pen}")
    print(f"適用後の攻撃力: {player.total_attack}")
    print(f"適用後の会心率: {player.crit_bonus}")
    print(f"適用後の防御無視: {player.total_armor_penetration}")

    # 装備なし: ratio=0 なので round(duration * 1.0) = duration, round(value * 1.0) = value
    assert player.attack_buff_turns == w_dur, f"雷霆のデフォルト持続は{w_dur}ターンのはず"
    assert player.attack_buff_val == w_val,    f"雷霆のデフォルト効果は+{w_val}のはず"
    assert player.attack_buff_crit == 10,  "crit_bonusはitems.ymlから10が読まれるはず"
    assert abs(player.attack_buff_armor_pen - 0.20) < 0.001, "armor_penはitems.ymlから0.20が読まれるはず"
    assert abs(player.crit_bonus - 0.1) < 0.001, "バフ中のcrit_bonusプロパティは+0.1（10%）のはず"
    assert abs(player.total_armor_penetration - 0.20) < 0.001, "バフ中のarmor_penetrationは+20%のはず"

    # バフを一度クリア
    player.attack_buff_turns = 0
    player.attack_buff_val = 0
    player.attack_buff_crit = 0
    player.attack_buff_armor_pen = 0.0

    print("\n--- 3. 戦士の剣と鎧を装備して雷霆の秘薬を使用 ---")
    # 戦士の剣と鎧をインベントリに追加して装備
    sword_inst = player.equip_weapon_by_key("fighters_sword")
    player.equipped_weapon = sword_inst.iid
    player.weapon = player._get_weapon_instance("fighters_sword", 0)

    armor_inst = player.equip_armor_by_key("fighters_armor")
    player.change_armor(armor_inst.iid)

    print(f"装備確認: 武器={sword_inst.key}, 鎧={armor_inst.key}")
    # 新しいratioボーナスの確認
    print(f"装備魔法ボーナス buff_value_ratio: {player.get_magic_bonus('buff_value_ratio')}")
    print(f"装備魔法ボーナス buff_duration_ratio: {player.get_magic_bonus('buff_duration_ratio')}")

    player.add_item_to_inventory("warrior_potion")
    msg = use_consumable("warrior_potion", player)
    print(msg)
    print(f"バフ状態: attack_buff_turns={player.attack_buff_turns}, attack_buff_val={player.attack_buff_val}")
    print(f"適用後の攻撃力: {player.total_attack} (ベース+武器+バフ)")

    # 剣: buff_value_ratio=0.2  → round(w_dur * 1.4), round(w_val * 1.4)
    # 鎧: buff_duration_ratio=0.2
    expected_w_turns = round(w_dur * 1.4)
    expected_w_val = round(w_val * 1.4)
    assert player.attack_buff_turns == expected_w_turns, f"戦士の鎧(0.2)+剣(0.2)で持続がround({w_dur}*1.4)={expected_w_turns}Tになるはず"
    assert player.attack_buff_val == expected_w_val,    f"戦士の鎧(0.2)+剣(0.2)で効果量がround({w_val}*1.4)={expected_w_val}になるはず"
    assert abs(player.crit_bonus - 0.1) < 0.001, "装備があっても雷霆バフによる会心率+0.1（10%）は維持されるはず"
    assert abs(player.total_armor_penetration - 0.40) < 0.001, "装備があっても雷霆バフによる防御無視+20%は維持されるはず"

    # 雷霆バフを一度クリア
    player.attack_buff_turns = 0
    player.attack_buff_val = 0
    player.attack_buff_crit = 0
    player.attack_buff_armor_pen = 0.0

    print("\n--- 4. 燕の秘薬の動作確認（戦士シリーズ装備中） ---")
    player.add_item_to_inventory("pilgrim_potion")
    msg = use_consumable("pilgrim_potion", player)
    print(msg)
    print(f"バフ状態: regen_buff_turns={player.regen_buff_turns}, regen_buff_val={player.regen_buff_val}")
    print(f"  regen_buff_heal_boost={player.regen_buff_heal_boost}")

    # 燕: 持続 * 1.4, 効果量 * 1.4
    expected_p_turns = round(p_dur * 1.4)
    expected_p_val = round(p_val * 1.4)
    assert player.regen_buff_turns == expected_p_turns,  f"戦士の鎧+剣で燕の持続がround({p_dur}*1.4)={expected_p_turns}Tになるはず"
    assert player.regen_buff_val == expected_p_val,     f"戦士の剣で燕の効果量がround({p_val}*1.4)={expected_p_val}になるはず"
    assert abs(player.regen_buff_heal_boost - 0.20) < 0.001, "heal_boostはitems.ymlから0.20が読まれるはず"

    # 4-1. 毎ターン直接回復の検証
    player.max_hp = 100
    player.hp = 90
    player.regen_pool = 0.0

    class MockDungeon:
        def __init__(self):
            self.tile_size = 32
            self.magic_effects = []
            self.enemies = []

    dungeon = MockDungeon()
    player.apply_turn_effects(dungeon)
    expected_hp = 90 + expected_p_val
    print(f"1ターン後のHP: {player.hp} ({expected_hp}のはず)")
    assert player.hp == expected_hp, f"燕バフ中の毎ターン直接回復(+{expected_p_val})が適用されるはず"

    # 4-2. 回復アイテム効果+20%の検証
    player.hp = 50
    player.items = []
    player.add_item_to_inventory("hp_potion")
    msg_heal = use_consumable("hp_potion", player)
    print(msg_heal)
    # hp_potionのベース回復量だが、heal_boost=0.20で回復
    expected_heal = round(hp_pot_heal * 1.2)
    expected_hp_after_heal = min(player.max_hp, 50 + expected_heal)
    print(f"回復後のHP: {player.hp} ({expected_hp_after_heal}のはず)")
    assert player.hp == expected_hp_after_heal, f"燕バフにより回復薬の回復量がround({hp_pot_heal}*1.2)={expected_heal}になるはず"

    # 燕バフをクリア
    player.regen_buff_turns = 0
    player.regen_buff_val = 0
    player.regen_buff_heal_boost = 0.0

    print("\n--- 5. 賢者の秘薬の動作確認（戦士シリーズ装備中） ---")
    player.add_item_to_inventory("sage_potion")

    # 杖をインベントリに用意してチャージを減らしておく
    stave1 = StaveInstance("fire_stave", charges=2)
    stave2 = StaveInstance("heal_stave", charges=0)
    player.stave_inventory = [stave1, stave2]

    msg = use_consumable("sage_potion", player)
    print(msg)
    print(f"バフ状態: magic_buff_turns={player.magic_buff_turns}, magic_buff_val={player.magic_buff_val}")
    print(f"適用後の魔法(炎ダメージ)ボーナス: {player.get_magic_bonus('fire_damage')}")
    print(f"適用後の会心ボーナス: {player.crit_bonus}")

    # 賢者: 持続 * 1.4, 効果量 * 1.4, stave_recovery=3(items.ymlから)
    expected_s_turns = round(s_dur * 1.4)
    expected_s_val = s_val * 1.4
    assert player.magic_buff_turns == expected_s_turns,  f"戦士の鎧+剣で賢者の持続がround({s_dur}*1.4)={expected_s_turns}Tになるはず"
    assert abs(player.magic_buff_val - expected_s_val) < 0.001, f"戦士の鎧+剣で賢者の効果量が{s_val}*1.4={expected_s_val}になるはず"
    assert abs(player.crit_bonus - 0.0) < 0.001, "賢者バフで会心率は上昇しないはず"
    assert stave1.charges == 5,            "stave1のチャージがitems.ymlのstave_recovery=3で+3され5になるはず"
    assert stave2.charges == 3,            "stave2のチャージが+3されるはず"

    # 賢者バフクリア
    player.magic_buff_turns = 0
    player.magic_buff_val = 0

    print("\n--- 6. 戦士の盾装備時の杖の消費確率節約の検証（無効化の確認） ---")
    shield_inst = player.equip_shield_by_key("fighters_sheld")
    player.change_shield(shield_inst.iid)
    print(f"装備確認: 盾={shield_inst.key}")
    print(f"装備魔法ボーナス stave_bonus: {player.get_magic_bonus('stave_bonus')}%")

    assert player.get_magic_bonus('stave_bonus') == 1, "戦士の盾からstave_bonusが削除され、剣の1%のみになるはず"

    # 実際に杖を振って、常に消費されることを確認
    stave = StaveInstance("fire_stave", charges=5)
    class MockDialog:
        def __init__(self):
            self.text = ""
            self.is_active = False
    dialog = MockDialog()

    execute_stave(player, stave, dungeon, dialog)
    print(f"杖使用後の残り回数: {stave.charges} (4のはず)")
    assert stave.charges == 4, "stave_bonusが0%なので確実に回数が減るはず"

    print("\n🎉 すべてのテスト項目をパスしました！")

if __name__ == "__main__":
    try:
        test_potions_and_fighter_set()
        print("\n🎉 全ての秘薬機能テストに合格しました！")
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
