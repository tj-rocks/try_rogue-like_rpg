
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
from systems.death_handler import handle_death_sequence
from constants import DOCTOR_FEE

def test_death_penalty():
    print("--- 死亡ペナルティテスト開始 ---")
    
    player = Player()
    player.coin = 1000
    player.bank_coin = 500
    player.hp = 0
    player.is_dead = True
    
    # 装備を持たせる
    w_inst = player.equip_weapon_by_key("iron_sword")
    player.equipped_weapon = w_inst.iid
    a_inst = player.equip_armor_by_key("leather_breastplate")
    player.equipped_armor = a_inst.iid
    
    # モックの準備
    dungeon = MagicMock()
    dungeon.tile_size = 64
    dialog = MagicMock()
    dialog.is_active = False
    game_state = {"death_sequence_step": 3, "death_timer": 1} # ステップ3(ペナルティ適用直前)から開始
    
    # warp_to_floor をモックして副作用（ファイルのロード等）を防ぐ
    with patch("systems.dungeon.warp_to_floor") as mock_warp:
        with patch("components.sprites.player.Player.save_to_file"): # セーブもスキップ
            handle_death_sequence(player, dungeon, dialog, game_state)
    
    # 検証: 所持金
    # 1. 元 1000 -> 半分で 500
    # 2. 治療費 (DOCTOR_FEE) が引かれる
    expected_coin = 500 - DOCTOR_FEE
    print(f"所持金検証: 期待値 {expected_coin}, 実際 {player.coin}")
    assert player.coin == expected_coin
    
    # 検証: 装備保存 (装備していた物は残り、未装備は失われる)
    print(f"装備検証: weapon_inventory={len(player.weapon_inventory)}, equipped_weapon={player.equipped_weapon}")
    assert len(player.weapon_inventory) == 1
    assert player.weapon_inventory[0].key == "iron_sword"
    assert len(player.armor_inventory) == 1
    assert player.armor_inventory[0].key == "leather_breastplate"
    
    # 検証: 呪い進行
    print(f"呪い検証: curse_level={player.curse_level}, cursed_stats={player.cursed_stats}")
    assert player.curse_level == 1
    assert len(player.cursed_stats) == 1

    # 検証: 復活
    assert player.hp == player.max_hp
    assert player.is_dead == False
    
    print("[OK] 死亡ペナルティテスト合格！")

def test_death_debt():
    print("--- 死亡時借金テスト開始 ---")
    
    player = Player()
    player.coin = 10 # 治療費に足りない
    player.bank_coin = 0
    player.hp = 0
    player.is_dead = True
    
    dungeon = MagicMock()
    dialog = MagicMock()
    game_state = {"death_sequence_step": 3, "death_timer": 1}
    
    # warp_to_floor をモック
    with patch("systems.dungeon.warp_to_floor"):
        with patch("components.sprites.player.Player.save_to_file"):
            handle_death_sequence(player, dungeon, dialog, game_state)
            
    # 検証: 借金 (10 // 2 = 5. 5 - DOCTOR_FEE = 負の値)
    # 現在 DOCTOR_FEE = 20 なので、 5 - 20 = -15
    print(f"借金検証: 実際 {player.coin}")
    assert player.coin < 0
    print("[OK] 死亡時借金テスト合格！")

def test_respawn_position():
    print("--- 復活位置検証テスト開始 ---")
    from systems.dungeon import Dungeon
    
    player = Player()
    # 0階（村）のダミーダンジョン
    dungeon = Dungeon(level=0, player=player)
    
    # 医者の位置を強制設定（通常はマップ読み込み時に設定される）
    dungeon.clinic_pos = (10, 20)
    ts = dungeon.tile_size
    
    # 死亡フラグを立ててスポーン位置設定を呼び出す
    # spawn_reason="continue" はセーブデータからの復旧時などを想定
    dungeon.set_spawn_position(player, spawn_reason="continue", is_death=True)
    
    expected_x = (dungeon.clinic_pos[0] + 1) * ts
    expected_y = dungeon.clinic_pos[1] * ts
    
    print(f"座標検証: 期待値 ({expected_x}, {expected_y}), 実際 ({player.x}, {player.y})")
    assert player.x == expected_x
    assert player.y == expected_y
    
    print("[OK] 復活位置検証テスト合格！")

def test_poison_death_revival():
    print("--- 毒状態での死亡・クリニック復活テスト開始 ---")
    
    from systems.dungeon import Dungeon
    player = Player()
    player.hp = 0
    player.is_dead = True
    player.condition = "poison"
    player.status_timer = 10
    
    dungeon = Dungeon(level=0, player=player)
    # クリニックの位置を設定
    dungeon.clinic_pos = (10, 20)
    
    dialog = MagicMock()
    game_state = {"death_sequence_step": 3, "death_timer": 1}
    
    # patchを使って実際にwarp_to_floorが呼ばれた際の処理をシミュレート
    with patch("systems.dungeon.warp_to_floor") as mock_warp:
        # warp_to_floor(0, ...) が呼ばれたら、実際に set_spawn_position を実行するように設定
        def side_effect(floor, p, **kwargs):
            if floor == 0:
                dungeon.set_spawn_position(p, spawn_reason="continue", is_death=True)
            return dungeon
        mock_warp.side_effect = side_effect
        
        with patch("components.sprites.player.Player.save_to_file"):
            handle_death_sequence(player, dungeon, dialog, game_state)
    
    # 1. 座標検証 (医者の横 (11, 20) になっているか)
    ts = 64
    expected_x = (10 + 1) * ts
    expected_y = 20 * ts
    print(f"座標検証: 期待値 ({expected_x}, {expected_y}), 実際 ({player.x}, {player.y})")
    assert player.x == expected_x
    assert player.y == expected_y
    
    # 2. ステータス検証 (復活しているか & 毒が治っているか)
    print(f"状態検証: hp={player.hp}, condition={player.condition}")
    assert not player.is_dead
    assert player.hp == player.max_hp
    assert player.condition == "normal"
    assert player.status_timer == 0
    
    print("[OK] 毒状態での死亡・クリニック復活テスト合格！")

def test_comprehensive_curse_system():
    print("--- 呪いシステムの包括的結合テスト開始 ---")
    
    player = Player()
    player.coin = 5000
    player.bank_coin = 0
    
    # 1. 装備品およびロスト対象アイテム（予備装備、消耗品、杖）を用意
    w_equipped = player.equip_weapon_by_key("iron_sword")
    player.equipped_weapon = w_equipped.iid
    
    w_spare = player.equip_weapon_by_key("wooden_stick") # 未装備の予備武器
    
    a_equipped = player.equip_armor_by_key("leather_breastplate")
    player.equipped_armor = a_equipped.iid
    
    # 消耗品と杖を追加
    from components.sprites.player import StaveInstance
    player.stave_inventory.append(StaveInstance("fire_stave", 3))
    player.items.append({"key": "potion_red", "count": 2})
    
    # 基準となる初期ステータス（無呪い状態）の記録
    base_attack = player.total_attack
    base_defense = player.total_defense
    base_hp = player.max_hp
    base_accuracy = player.total_accuracy_close
    base_evasion = player.eva_bonus
    
    print(f"初期ステータス: ATK={base_attack}, DEF={base_defense}, HP={base_hp}, ACC={base_accuracy}, EVA={base_evasion}")
    
    # 2. 5回連続で死亡させて、呪い進行とステータス低下を追跡
    dungeon = MagicMock()
    dungeon.tile_size = 64
    dialog = MagicMock()
    game_state = {"death_sequence_step": 3, "death_timer": 1}
    
    # 1回目の死亡
    player.hp = 0
    player.is_dead = True
    with patch("systems.dungeon.warp_to_floor"):
        with patch("components.sprites.player.Player.save_to_file"):
            handle_death_sequence(player, dungeon, dialog, game_state)
            
    # 検証: 装備品以外は全ロストしているか？
    print("死亡ロスト検証...")
    assert len(player.weapon_inventory) == 1
    assert player.weapon_inventory[0].iid == w_equipped.iid # 装備中のみ残る
    assert len(player.armor_inventory) == 1
    assert player.armor_inventory[0].iid == a_equipped.iid # 装備中のみ残る
    assert len(player.stave_inventory) == 0 # 杖はロスト
    assert len(player.items) == 0 # 消耗品はロスト
    print("[OK] 装備保存＆その他ロスト検証成功！")
    
    # 呪い進行の検証 (1段階目)
    assert player.curse_level == 1
    assert len(player.cursed_stats) == 1
    debuffed_stat_1 = player.cursed_stats[0]
    print(f"1回目の死亡: 呪いレベル=1, デバフ対象={debuffed_stat_1}")
    
    # 低下補正が適用されていることの検証
    if debuffed_stat_1 == "attack":
        assert player.total_attack < base_attack
    elif debuffed_stat_1 == "defense":
        assert player.total_defense < base_defense
    elif debuffed_stat_1 == "hp":
        assert player.max_hp < base_hp
    elif debuffed_stat_1 == "accuracy":
        assert player.total_accuracy_close < base_accuracy
    elif debuffed_stat_1 == "evasion":
        assert player.eva_bonus < base_evasion
    print("[OK] 1段階目デバフ適用検証成功！")
    
    # 2回目〜5回目の死亡（5段階マックスまで）
    for death_idx in range(2, 6):
        player.hp = 0
        player.is_dead = True
        game_state = {"death_sequence_step": 3, "death_timer": 1}
        with patch("systems.dungeon.warp_to_floor"):
            with patch("components.sprites.player.Player.save_to_file"):
                handle_death_sequence(player, dungeon, dialog, game_state)
                
        # 呪い進行とデバフスロット数の検証
        print(f"{death_idx}回目の死亡: 呪いレベル={player.curse_level}, デバフ対象リスト={player.cursed_stats}")
        assert player.curse_level == death_idx
        assert len(player.cursed_stats) == death_idx
        
    print("[OK] 5段階最大レベル到達＆重複なし5個デバフ検証成功！")
    
    # 6回目の死亡（5段階上限でそれ以上進行しないことを検証）
    player.hp = 0
    player.is_dead = True
    game_state = {"death_sequence_step": 3, "death_timer": 1}
    with patch("systems.dungeon.warp_to_floor"):
        with patch("components.sprites.player.Player.save_to_file"):
            handle_death_sequence(player, dungeon, dialog, game_state)
            
    print(f"6回目の死亡(上限チェック): 呪いレベル={player.curse_level}, デバフ対象={player.cursed_stats}")
    assert player.curse_level == 5
    assert len(player.cursed_stats) == 5
    
    # 全てのステータスに低下補正が掛かっていることの検証
    assert player.total_attack < base_attack
    assert player.total_defense < base_defense
    assert player.max_hp < base_hp
    assert player.total_accuracy_close < base_accuracy
    assert player.eva_bonus < base_evasion
    print("[OK] 5段階上限キャップ＆全ステータス低下補正検証成功！")
    
    # 3. ギルドでの治療シミュレーション (1段階ずつ治療してデバフ消失を確認)
    import random
    while player.curse_level > 0:
        prev_level = player.curse_level
        
        # ギルド治療の実行
        player.curse_level -= 1
        removed = random.choice(player.cursed_stats)
        player.cursed_stats.remove(removed)
        
        print(f"ギルド治療: レベル {prev_level} -> {player.curse_level}, 解除デバフ={removed}")
        assert player.curse_level == prev_level - 1
        assert removed not in player.cursed_stats
        
        # 治療されたステータスが元の正常値に戻っていることの検証
        if removed == "attack":
            assert player.total_attack == base_attack
        elif removed == "defense":
            assert player.total_defense == base_defense
        elif removed == "hp":
            assert player.max_hp == base_hp
        elif removed == "accuracy":
            assert player.total_accuracy_close == base_accuracy
        elif removed == "evasion":
            assert player.eva_bonus == base_evasion
            
    # 全快状態の検証
    assert player.curse_level == 0
    assert len(player.cursed_stats) == 0
    assert player.total_attack == base_attack
    assert player.total_defense == base_defense
    assert player.max_hp == base_hp
    assert player.total_accuracy_close == base_accuracy
    assert player.eva_bonus == base_evasion
    print("[OK] ギルド呪い治療＆ステータス完全全快検証成功！")
    print("--- 呪いシステムの包括的結合テスト合格！ ---")

if __name__ == "__main__":
    try:
        test_death_penalty()
        test_death_debt()
        test_respawn_position()
        test_poison_death_revival()
        test_comprehensive_curse_system()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
