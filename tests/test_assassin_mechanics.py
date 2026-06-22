
import pygame
import sys
import os
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["TEST_MODE"] = "1"

from systems.combat_handler import _is_back_attack, _is_frontal_attack, calculate_damage, deal_damage
from constants import TILE_SIZE

def make_combatant(x, y, facing="down", flank_backstab=0, stupidity_proc_chance=0.0, stupidity_proc_amount=0,
                   attack=10, hp=100, defense=0, crit_rate=0.0, accuracy_close=100, accuracy_ranged=100,
                   evasion=0, stupidity=0):
    """テスト用のシンプルな戦闘オブジェクトを作成する"""
    class Combatant:
        def take_damage(self, amount):
            self.hp = max(0, self.hp - amount)
    c = Combatant()
    c.x, c.y = x * TILE_SIZE, y * TILE_SIZE
    c.facing = facing
    c.total_flank_backstab = flank_backstab
    c.total_stupidity_proc_chance = stupidity_proc_chance
    c.total_stupidity_proc_amount = stupidity_proc_amount
    c.attack = attack
    c.hp = hp
    c.defense = defense
    c.crit_rate = crit_rate
    c.accuracy_close = accuracy_close
    c.accuracy_ranged = accuracy_ranged
    c.evasion = evasion
    c.stupidity = stupidity
    c.stupidity_temp = 0
    c.name = "テスト"
    c.is_god = False
    c.invincible_turns = 0
    c.condition = "normal"
    c.status_to_inflict = None
    c.status_chance = 100
    c.total_stupidity = 0
    c.total_backstab_crit_bonus = 0.0
    c.width = TILE_SIZE
    c.height = TILE_SIZE
    return c


# ─────────────────────────────────────────────
# テスト1: 通常の背後判定（flank_backstab なし）
# ─────────────────────────────────────────────
def test_normal_backstab():
    print("\n--- テスト1: 通常の背後判定 ---")
    # 敵が下向き → 上から攻撃 → 背後
    target   = make_combatant(5, 5, facing="down")
    attacker = make_combatant(5, 4, flank_backstab=0)  # 上にいる
    result = _is_back_attack(attacker, target)
    assert result == True, f"背後判定が False になっている (expected True)"
    print("[OK] 背後から攻撃 → True")

    # 敵が下向き → 下から攻撃 → 正面
    attacker2 = make_combatant(5, 6, flank_backstab=0)  # 下にいる（正面）
    result2 = _is_back_attack(attacker2, target)
    assert result2 == False, f"正面判定が True になっている (expected False)"
    print("[OK] 正面から攻撃 → False")

    # 敵が下向き → 右から攻撃 → 側面（通常は背後でない）
    attacker3 = make_combatant(6, 5, flank_backstab=0)  # 右にいる（側面）
    result3 = _is_back_attack(attacker3, target)
    assert result3 == False, f"側面判定が True になっている (expected False, no flank_backstab)"
    print("[OK] 側面から攻撃（flank_backstab=0） → False")


# ─────────────────────────────────────────────
# テスト2: flank_backstab 3以上で側面も背後扱い
# ─────────────────────────────────────────────
def test_flank_backstab():
    print("\n--- テスト2: flank_backstab による側面背後 ---")
    target = make_combatant(5, 5, facing="down")

    # 側面（右）からの攻撃 + flank_backstab=3 → 背後扱い
    attacker = make_combatant(6, 5, flank_backstab=3)
    result = _is_back_attack(attacker, target)
    assert result == True, f"flank_backstab=3 の側面攻撃が True でない (expected True)"
    print("[OK] 側面（flank_backstab=3） → True（背後扱い）")

    # 側面（左）からの攻撃 + flank_backstab=3 → 背後扱い
    attacker2 = make_combatant(4, 5, flank_backstab=3)
    result2 = _is_back_attack(attacker2, target)
    assert result2 == True, f"flank_backstab=3 の左側面攻撃が True でない (expected True)"
    print("[OK] 左側面（flank_backstab=3） → True（背後扱い）")

    # 正面からの攻撃 + flank_backstab=3 → 背後扱いにならない
    front = make_combatant(5, 6, flank_backstab=3)  # 正面（下にいる）
    result3 = _is_back_attack(front, target)
    assert result3 == False, f"正面攻撃が True になっている（flank_backstab=3でも正面は除外）"
    print("[OK] 正面（flank_backstab=3） → False（正面は除外）")

    # flank_backstab=2 では発動しない
    attacker4 = make_combatant(6, 5, flank_backstab=2)
    result4 = _is_back_attack(attacker4, target)
    assert result4 == False, f"flank_backstab=2 で発動してはいけない (expected False)"
    print("[OK] 側面（flank_backstab=2） → False（閾値未満）")


# ─────────────────────────────────────────────
# テスト3: stupidity_temp が攻撃ヒット時に上昇する
# ─────────────────────────────────────────────
def test_stupidity_temp_proc():
    print("\n--- テスト3: stupidity_temp の発動 ---")
    random.seed(0)  # 再現性確保

    # proc_chance=1.0（必ず発動）でテスト
    attacker = make_combatant(5, 5, stupidity_proc_chance=1.0, stupidity_proc_amount=3, attack=50)
    target   = make_combatant(5, 6)
    target.facing = "down"
    assert target.stupidity_temp == 0, "初期値が0でない"

    msg, dmg, is_crit, _ = deal_damage(attacker, target)
    assert not (dmg == 0), "ダメージが0（ミス）の場合テストが無効"
    assert target.stupidity_temp == 3, f"stupidity_temp が 3 になっていない: {target.stupidity_temp}"
    print(f"[OK] proc_chance=1.0, amount=3 → stupidity_temp={target.stupidity_temp}")

    # stupidity_temp は加算される（複数回ヒット時）
    target2 = make_combatant(5, 6)
    target2.facing = "down"
    deal_damage(attacker, target2)
    deal_damage(attacker, target2)
    assert target2.stupidity_temp == 6, f"2ヒット後 stupidity_temp が 6 でない: {target2.stupidity_temp}"
    print(f"[OK] 2回ヒット後 stupidity_temp={target2.stupidity_temp}（加算される）")


# ─────────────────────────────────────────────
# テスト4: stupidity_temp リセット後の判定
# ─────────────────────────────────────────────
def test_stupidity_temp_reset():
    print("\n--- テスト4: stupidity_temp リセット ---")
    attacker = make_combatant(5, 5, stupidity_proc_chance=1.0, stupidity_proc_amount=3, attack=50)
    target   = make_combatant(5, 6)
    target.facing = "down"

    deal_damage(attacker, target)
    assert target.stupidity_temp > 0, "ヒット後 stupidity_temp が上昇していない"
    before = target.stupidity_temp

    # entity_handler がターン後にリセットするのと同様の処理
    target.stupidity_temp = 0
    assert target.stupidity_temp == 0, "リセット後も 0 でない"
    print(f"[OK] ヒット後 stupidity_temp={before} → リセット後 stupidity_temp=0")


# ─────────────────────────────────────────────
# テスト5: proc_chance=0.0 のとき発動しない
# ─────────────────────────────────────────────
def test_stupidity_temp_no_proc():
    print("\n--- テスト5: proc_chance=0.0 では発動しない ---")
    attacker = make_combatant(5, 5, stupidity_proc_chance=0.0, stupidity_proc_amount=3, attack=50)
    target   = make_combatant(5, 6)
    target.facing = "down"

    for _ in range(20):
        deal_damage(attacker, target)

    assert target.stupidity_temp == 0, f"proc_chance=0.0 なのに stupidity_temp={target.stupidity_temp}"
    print("[OK] proc_chance=0.0 → 20回ヒット後も stupidity_temp=0")


# ─────────────────────────────────────────────
# テスト6: アサシン3部位の合計値チェック（YAMLから読み込み）
# ─────────────────────────────────────────────
def test_assassin_set_totals():
    print("\n--- テスト6: アサシン3部位の合計値 ---")
    pygame.init()
    screen = pygame.display.set_mode((800, 600))

    from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA
    from components.sprites.player import EquipInstance

    dagger = EquipInstance("weapon", "assassin_dagger")
    armor  = EquipInstance("armor",  "assassin_light_armor")
    shield = EquipInstance("shield", "assassin_buckler")

    assert WEAPON_DATA.get("assassin_dagger"),      "assassin_dagger がロードされていない"
    assert ARMOR_DATA.get("assassin_light_armor"),  "assassin_light_armor がロードされていない"
    assert SHIELD_DATA.get("assassin_buckler"),     "assassin_buckler がロードされていない"

    for name, eq in [("dagger", dagger), ("armor", armor), ("shield", shield)]:
        fb  = eq.get_stat("flank_backstab", 0)
        spc = eq.get_stat("stupidity_proc_chance", 0.0)
        spa = eq.get_stat("stupidity_proc_amount", 0)
        bsb = eq.get_stat("backstab_crit_bonus", 0.0)
        print(f"  {name}: flank_backstab={fb}, proc_chance={spc}, proc_amount={spa}, backstab_crit={bsb}")
        assert fb  == 1,   f"{name} の flank_backstab が 1 でない: {fb}"
        assert spc == 0.1, f"{name} の stupidity_proc_chance が 0.1 でない: {spc}"
        assert spa == 1,   f"{name} の stupidity_proc_amount が 1 でない: {spa}"
        assert bsb == {"dagger": 0.1, "armor": 0.2, "shield": 0.2}[name], f"{name} の backstab_crit_bonus が期待値でない: {bsb}"

    print("[OK] 各部位の個別値が正しい")

    # 合計値（3部位）
    total_flank = sum(eq.get_stat("flank_backstab", 0) for eq in [dagger, armor, shield])
    total_chance = sum(eq.get_stat("stupidity_proc_chance", 0.0) for eq in [dagger, armor, shield])
    total_amount = sum(eq.get_stat("stupidity_proc_amount", 0) for eq in [dagger, armor, shield])
    total_crit = sum(eq.get_stat("backstab_crit_bonus", 0.0) for eq in [dagger, armor, shield])

    print(f"  合計: flank_backstab={total_flank}, proc_chance={round(total_chance,2)}, proc_amount={total_amount}, backstab_crit={round(total_crit,2)}")
    assert total_flank  == 3,   f"3部位合計 flank_backstab が 3 でない: {total_flank}"
    assert round(total_chance, 2) == 0.3, f"3部位合計 stupidity_proc_chance が 0.3 でない: {total_chance}"
    assert total_amount == 3,   f"3部位合計 stupidity_proc_amount が 3 でない: {total_amount}"
    assert round(total_crit, 2) == 0.5, f"3部位合計 backstab_crit_bonus が 0.5 でない: {total_crit}"
    print("[OK] 3部位合計値が正しい（flank=3, chance=0.3, amount=3, crit=0.5）")

    pygame.quit()


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((800, 600))

    tests = [
        test_normal_backstab,
        test_flank_backstab,
        test_stupidity_temp_proc,
        test_stupidity_temp_reset,
        test_stupidity_temp_no_proc,
        test_assassin_set_totals,
    ]

    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {e}")

    print(f"\n========================================")
    print(f"アサシン機能テスト: {passed} / {len(tests)} 合格")
    print(f"========================================")

    pygame.quit()
    sys.exit(0 if passed == len(tests) else 1)
