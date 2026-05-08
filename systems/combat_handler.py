import random
from wordings import Text

def _is_frontal_attack(attacker, target):
    """
    攻撃が「正面から」かどうかを判定する。
    """
    facing = getattr(target, "facing", None)
    if not facing:
        return False
    from constants import TILE_SIZE
    ax, ay = int((attacker.x + TILE_SIZE / 2) // TILE_SIZE), int((attacker.y + TILE_SIZE / 2) // TILE_SIZE)
    tx, ty = int((target.x + TILE_SIZE / 2) // TILE_SIZE), int((target.y + TILE_SIZE / 2) // TILE_SIZE)
    
    if facing == "left"  and ax < tx: return True
    if facing == "right" and ax > tx: return True
    if facing == "up"    and ay < ty: return True
    if facing == "down"  and ay > ty: return True
    return False

def _is_back_attack(attacker, target):
    """
    攻撃が「背後から」かどうかを判定する。
    """
    facing = getattr(target, "facing", None)
    if not facing:
        return False
        
    from constants import TILE_SIZE
    ax, ay = int((attacker.x + TILE_SIZE / 2) // TILE_SIZE), int((attacker.y + TILE_SIZE / 2) // TILE_SIZE)
    tx, ty = int((target.x + TILE_SIZE / 2) // TILE_SIZE), int((target.y + TILE_SIZE / 2) // TILE_SIZE)
    
    if facing == "left"  and ax > tx: return True
    if facing == "right" and ax < tx: return True
    if facing == "up"    and ay > ty: return True
    if facing == "down"  and ay < ty: return True
    return False

def calculate_damage(attacker, target, is_magic=False, damage_mult=1.0):
    """
    攻撃者と対象のステータスからダメージを計算する。
    戻り値: (ダメージ量, クリティカルかどうか, ミスかどうか)
    """
    # 無敵状態のチェック
    if getattr(target, "is_god", False) or getattr(target, "invincible_turns", 0) > 0:
        return 0, False, False
        
    # 命中判定
    # 魔法攻撃は必中
    if is_magic:
        hit_rate = 1.0
    else:
        # 距離を算出して「近接」か「遠隔」かを判定する
        from constants import TILE_SIZE
        dist_x = abs(attacker.x - target.x) // TILE_SIZE
        dist_y = abs(attacker.y - target.y) // TILE_SIZE
        is_ranged = (dist_x + dist_y) > 1
        
        # 攻撃側の命中値 (Accuracy) の取得
        if is_ranged:
            accuracy = getattr(attacker, "total_accuracy_ranged", getattr(attacker, "accuracy_ranged", 100))
        else:
            accuracy = getattr(attacker, "total_accuracy_close", getattr(attacker, "accuracy_close", 100))
            
        evasion = getattr(target, "eva_bonus", 0)
        hit_rate = (accuracy - evasion) / 100.0
        
        # [NEW] 盾によるブロック判定を命中率に統合（正面からの攻撃のみ）
        if _is_frontal_attack(attacker, target):
            if is_ranged:
                block_chance = getattr(target, "block_chance_ranged", getattr(target, "block_chance", 0.0))
            else:
                block_chance = getattr(target, "block_chance_close", getattr(target, "block_chance", 0.0))
            
            if block_chance > 0.0:
                hit_rate -= block_chance
    
    # 命中率の上下限 (魔法以外は最低5%は当たる、最大99%)
    if is_magic:
        is_miss = False
    else:
        hit_rate = max(0.05, min(0.99, hit_rate))
        is_miss = random.random() >= hit_rate
    
    if is_miss:
        return 0, False, True # ミス！ (盾で防いだ場合もここに含まれる)
        
    # 攻撃力の算出
    base_atk = getattr(attacker, "total_attack", attacker.attack)
    base_atk = int(base_atk * damage_mult)
    weapon = getattr(attacker, "weapon", None)
    
    # クリティカル率の決定 (基本値 1% または モンスター固有値)
    crit_rate = getattr(attacker, "crit_rate", 0.01)
    
    if weapon:
        crit_rate = weapon.data.get("crit_rate", 0.01)
    
    # クリティカル率補正の加算
    crit_bonus = getattr(attacker, "crit_bonus", 0)
    crit_rate += crit_bonus
    
    # [NEW] バックアタックボーナス (+25%)
    if _is_back_attack(attacker, target):
        crit_rate += 0.25
    
    # [NEW] 会心率の上限キャップ適用
    from constants import CRITICAL_RATE_MAX
    crit_rate = min(CRITICAL_RATE_MAX, crit_rate)
    
    # クリティカル判定
    is_critical = random.random() < crit_rate
    calc_atk = base_atk * 2 if is_critical else base_atk
    
    # 防御力によるベースダメージの算出 (防御力もボーナス込みを参照)
    defense = getattr(target, "total_defense", getattr(target, "defense", 0))
    
    # [NEW] 武器の防御力貫通（Armor Penetration）判定
    if weapon and weapon.data.get("armor_penetration"):
        defense = 0
        
    base_dmg = max(0.1, calc_atk - defense) # 最低0.1ダメージ保証
    
    # 乱数要素: 9割は保証、1割が乱数 (90-100%)
    from systems.math_utils import hardcore_round
    # ダメージ計算も小数点第一位までで行い、第二位を繰り上げ
    raw_damage = base_dmg * (0.9 + random.uniform(0, 0.1))
    rounded_damage = hardcore_round(raw_damage, is_hp=False)
    
    # HPは整数なので、最終ダメージはさらに整数に繰り上げ
    final_damage = hardcore_round(rounded_damage, is_hp=True)
    final_damage = max(1, final_damage)
    
    return final_damage, is_critical, False


def deal_damage(attacker, target, is_magic=False, damage_mult=1.0):
    """
    ダメージを計算し、対象に適用し、メッセージを生成して返す。
    戻り値: (メッセージ, ダメージ量, クリティカルフラグ, ミスフラグ)
    """
    damage, is_critical, is_miss = calculate_damage(attacker, target, is_magic=is_magic, damage_mult=damage_mult)
    
    attacker_name = getattr(attacker, "name", "誰か")
    target_name = getattr(target, "name", "誰か")
    
    if is_miss:
        msg = "ミス " + Text.Combat.MISS.format(attacker=attacker_name, target=target_name)
        return msg, 0, False, True
    
    if damage == 0:
        msg = Text.Combat.BLOCK.format(target=target_name)
        return msg, 0, False, False
    
    target.take_damage(damage)
    
    # メッセージ生成
    if is_critical:
        # バックアタックかどうかでメッセージを豪華にする
        prefix = "背後を突いた " if _is_back_attack(attacker, target) else ""
        msg = prefix + Text.Combat.CRITICAL + Text.Combat.DAMAGE.format(attacker=attacker_name, target=target_name, damage=damage)
    else:
        msg = Text.Combat.DAMAGE.format(attacker=attacker_name, target=target_name, damage=damage)
        
    # --- [NEW] 状態異常の付与判定 ---
    status_to_add = getattr(attacker, "status_to_inflict", None)
    status_chance = getattr(attacker, "status_chance", 100)
    if status_to_add and not is_miss and damage > 0:
        if random.randint(1, 100) <= status_chance:
            # 対象がそのステータスを受け入れられる（condition属性を持っている）場合のみ付与
            if hasattr(target, "condition"):
                target.condition = status_to_add
                if status_to_add == "poison":
                    msg += f"\n{target_name}は毒を受けてしまった"

    target_hp = getattr(target, 'hp', '?')
    target_cond = getattr(target, 'condition', 'normal')
    print(f"[COMBAT] {attacker_name} -> {target_name}: Damage={damage}, Critical={is_critical}, Miss={is_miss}, TargetHP: {target_hp}, TargetCond: {target_cond}")
    return msg, damage, is_critical, False

