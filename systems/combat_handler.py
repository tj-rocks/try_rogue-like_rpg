import random
from constants import HIT_STUN_DURATION, ATTACK_ANIMATION_FRAMES
from wordings import Text


def _as_int_or_zero(value):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    return 0


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return False

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
    flank_backstab 合計が 2 以上の場合、側面（正面以外）も背後扱いにする。
    障害物（is_static）にはバックアタックを適用しない。
    """
    if getattr(target, "is_static", False):
        return False
    facing = getattr(target, "facing", None)
    if not facing:
        return False

    from constants import TILE_SIZE
    ax, ay = int((attacker.x + TILE_SIZE / 2) // TILE_SIZE), int((attacker.y + TILE_SIZE / 2) // TILE_SIZE)
    tx, ty = int((target.x + TILE_SIZE / 2) // TILE_SIZE), int((target.y + TILE_SIZE / 2) // TILE_SIZE)

    # 完全な背後
    if facing == "left"  and ax > tx: return True
    if facing == "right" and ax < tx: return True
    if facing == "up"    and ay > ty: return True
    if facing == "down"  and ay < ty: return True

    # 側面も背後扱いにするスキル（flank_backstab 合計 2 以上）
    flank = getattr(attacker, "total_flank_backstab", 0)
    if isinstance(flank, (int, float)) and flank >= 2:
        if not _is_frontal_attack(attacker, target):
            return True
    return False

def calculate_damage(attacker, target, is_magic=False, damage_mult=1.0):
    """
    攻撃者と対象のステータスからダメージを計算する。
    戻り値: (ダメージ量, クリティカルかどうか, ミスかどうか)
    """
    from constants import ENABLE_DEBUG_LOGGING

    # 無敵状態のチェック
    if _as_bool(getattr(target, "is_god", False)) or _as_int_or_zero(getattr(target, "invincible_turns", 0)) > 0:
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
            
        hit_rate = accuracy / 100.0
        
        # [NEW] 盾によるブロック判定を命中率に統合（正面からの攻撃のみ）
        if _is_frontal_attack(attacker, target):
            if is_ranged:
                block_chance = getattr(target, "block_chance_ranged", 0.0)
            else:
                block_chance = getattr(target, "block_chance_close", 0.0)
            
            if block_chance != 0.0:
                hit_rate -= block_chance
    
    # 命中率の上下限 (魔法以外は最低MIN_HIT_RATEは当たる、最大99%)
    if is_magic:
        is_miss = False
    else:
        from constants import MIN_HIT_RATE
        hit_rate = max(MIN_HIT_RATE, min(0.99, hit_rate))
        is_miss = random.random() >= hit_rate
    
    if is_miss:
        return 0, False, True # ミス！ (盾で防いだ場合もここに含まれる)
        
    # 攻撃力の算出
    base_atk = getattr(attacker, "total_attack", attacker.attack)
    base_atk = base_atk * damage_mult
    weapon = getattr(attacker, "weapon", None)
    
    # クリティカル率の決定 (基本値 1% または モンスター固有値)
    crit_rate = getattr(attacker, "crit_rate", 0.01)
    
    if weapon:
        crit_rate = weapon.data.get("crit_rate", 0.01)
    
    # クリティカル率補正の加算
    crit_bonus = getattr(attacker, "crit_bonus", 0)
    crit_rate += crit_bonus
    
    # [NEW] バックアタックボーナス（魔法攻撃には適用しない）
    is_backstab = (not is_magic) and _is_back_attack(attacker, target)
    import os as _os
    if _os.environ.get("DEBUG_MODE") == "1" and getattr(attacker, "total_flank_backstab", 0) > 0:
        print(f"[バックスタブ] {'✅ 成功' if is_backstab else '❌ 失敗'}")
    if is_backstab:
        from constants import BACKSTAB_CRIT_BONUS
        crit_rate += BACKSTAB_CRIT_BONUS
        if hasattr(attacker, "total_backstab_crit_bonus"):
            crit_rate += attacker.total_backstab_crit_bonus
    
    # [NEW] 会心率の上限キャップ適用
    from constants import CRITICAL_RATE_MAX
    crit_rate = min(CRITICAL_RATE_MAX, crit_rate)
    
    # クリティカル判定
    force_critical = _as_bool(getattr(attacker, "_force_critical_once", False))
    is_critical = force_critical or (random.random() < crit_rate)
    if force_critical:
        attacker._force_critical_once = False
    from constants import CRITICAL_DAMAGE_MULTIPLIER, BACKSTAB_CRITICAL_DAMAGE_MULTIPLIER
    if is_critical:
        crit_multiplier = BACKSTAB_CRITICAL_DAMAGE_MULTIPLIER if is_backstab else CRITICAL_DAMAGE_MULTIPLIER
    else:
        crit_multiplier = 1.0
    calc_atk = base_atk * crit_multiplier
    
    # 防御力によるベースダメージの算出 (防御力もボーナス込みを参照)
    defense = getattr(target, "total_defense", getattr(target, "defense", 0))
    


    
    # 防御力無視（Armor Penetration）の割合による減算判定
    penetration = 0.0
    if hasattr(attacker, "total_armor_penetration"):
        penetration = attacker.total_armor_penetration
    elif weapon:
        penetration = weapon.data.get("armor_penetration", 0.0)
        
    if isinstance(penetration, bool):
        penetration = 1.0 if penetration else 0.0
    elif not isinstance(penetration, (int, float)):
        penetration = 0.0
        
    pen_rate = min(1.0, max(0.0, penetration))
    # 割合軽減方式: Attack * (50 / (50 + Defense))
    defense = defense * (1.0 - pen_rate)
    defense = max(0.0, defense)
    base_dmg = calc_atk * (50.0 / (50.0 + defense))
    base_dmg = max(0.1, base_dmg) # 最低0.1ダメージ保証
    
    # 乱数要素: 9割は保証、2割が乱数 (90-110%)
    from systems.math_utils import hardcore_round
    # ダメージ計算も小数点第一位までで行い、第二位を繰り上げ
    raw_damage = base_dmg * (0.9 + random.uniform(0, 0.2))
    rounded_damage = hardcore_round(raw_damage, is_hp=False)
    
    # HPは整数なので、最終ダメージはさらに整数に繰り上げ
    final_damage = hardcore_round(rounded_damage, is_hp=True)
    final_damage = max(1, final_damage)
    
    # 被ダメ倍率（拘束等による弱点化）
    vulnerable_mult = getattr(target, "vulnerable_mult", None)
    if isinstance(vulnerable_mult, (int, float)) and vulnerable_mult != 1.0:
        final_damage = max(1, int(final_damage * vulnerable_mult))
    
    return final_damage, is_critical, False


def deal_damage(attacker, target, is_magic=False, damage_mult=1.0):
    """
    ダメージを計算し、対象に適用し、メッセージを生成して返す。
    戻り値: (メッセージ, ダメージ量, クリティカルフラグ, ミスフラグ)
    """
    import os as _os
    damage, is_critical, is_miss = calculate_damage(attacker, target, is_magic=is_magic, damage_mult=damage_mult)
    
    attacker_name = getattr(attacker, "name", "誰か")
    target_name = getattr(target, "name", "誰か")
    target_is_static = getattr(target, "is_static", False)
    
    if is_miss:
        msg = "ミス " + Text.Combat.MISS.format(attacker=attacker_name, target=target_name)
        return msg, 0, False, True
    
    if damage == 0:
        msg = Text.Combat.BLOCK.format(target=target_name)
        return msg, 0, False, False
    
    counter_ready_turns = _as_int_or_zero(getattr(target, "counter_ready_turns", 0))
    if (
        counter_ready_turns > 0
        and not is_magic
        and getattr(attacker, "__class__", None).__name__ == "Player"
    ):
        target.counter_ready_turns = 0
        target._force_critical_once = True
        if hasattr(target, "is_attacking"):
            target.is_attacking = True
            target.attack_timer = ATTACK_ANIMATION_FRAMES
            target.has_dealt_impact_damage = False
            target.current_attack_mode = "counter"
        counter_msg, _, _, _ = deal_damage(target, attacker, is_magic=False, damage_mult=1.25)
        counter_prefix = f"{target_name}のカウンター！\n{counter_msg}\n"
    else:
        counter_prefix = ""

    target.take_damage(damage)
    
    # メッセージ生成
    if is_critical:
        # バックアタックかどうかでメッセージを豪華にする（魔法攻撃は除外）
        is_backstab = (not is_magic) and _is_back_attack(attacker, target)
        if is_backstab and hasattr(target, "flash_color"):
            target.flash_color = (255, 50, 50)
        prefix = "背後を突いた " if is_backstab else ""
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
                elif status_to_add == "darkness":
                    msg += f"\n{target_name}は暗闇に包まれた！視界が狭まった！"

    # --- 敵の困惑（stupidity）上昇効果 ---
    if not target_is_static and not is_miss and damage > 0:
        stupidity_up = getattr(attacker, "total_stupidity", 0)
        if isinstance(stupidity_up, (int, float)) and stupidity_up > 0 and hasattr(target, "stupidity"):
            target.stupidity = min(10, target.stupidity + int(stupidity_up))
            msg += "\n" + Text.Combat.CONFUSED.format(target=target_name, amount=int(stupidity_up))

    # --- 敵の一時的 stupidity 上昇効果（装備スキル） ---
    if not target_is_static and not is_miss and damage > 0 and hasattr(target, "stupidity_temp"):
        total_confusion = getattr(attacker, "total_confusion", 0)
        if isinstance(total_confusion, int) and total_confusion >= 2:
            proc_chance = getattr(attacker, "total_stupidity_proc_chance", 0.0)
            if isinstance(proc_chance, (int, float)) and proc_chance > 0:
                rolled = random.random()
                if rolled < proc_chance:
                    proc_amount = getattr(attacker, "total_stupidity_proc_amount", 0)
                    if isinstance(proc_amount, (int, float)) and proc_amount > 0:
                        target.stupidity_temp += int(proc_amount)
                        msg += f"\n{target_name}は一時的に混乱した！"
                        if _os.environ.get("DEBUG_MODE") == "1":
                            print(f"[混乱] ✅ 成功")
                elif _os.environ.get("DEBUG_MODE") == "1":
                    print(f"[混乱] ❌ 失敗")

    # --- スタン効果（クリティカル時のみ発動） ---
    if not target_is_static and not is_miss and damage > 0 and is_critical and hasattr(target, "stun_turns"):
        total_stun = getattr(attacker, "total_stun", 0)
        stun_chance = getattr(attacker, "total_stun_proc_chance", 0.0)
        if isinstance(total_stun, int) and total_stun >= 2 and isinstance(stun_chance, (int, float)) and stun_chance > 0:
            stun_duration = getattr(attacker, "total_stun_duration", 1)
            if isinstance(stun_duration, (int, float)) and stun_duration > 0:
                target.stun_turns = int(stun_duration)
                if hasattr(target, "flash_color"):
                    target.flash_color = (50, 100, 255)
                msg += f"\n{target_name}はスタンした！"
                if _os.environ.get("DEBUG_MODE") == "1":
                    print(f"[スタン] ✅ クリティカル発動")

    # --- ライフスティール効果（クリティカル時のみ発動） ---
    if not target_is_static and not is_miss and damage > 0 and is_critical and hasattr(attacker, "hp"):
        total_lifesteal = getattr(attacker, "total_lifesteal", 0)
        if isinstance(total_lifesteal, int) and total_lifesteal >= 2:
            lifesteal_chance = getattr(attacker, "total_lifesteal_chance", 0.0)
            if isinstance(lifesteal_chance, (int, float)) and lifesteal_chance > 0:
                lifesteal_ratio = getattr(attacker, "total_lifesteal_ratio", 0.0)
                if isinstance(lifesteal_ratio, (int, float)) and lifesteal_ratio > 0:
                    heal_amount = int(damage * lifesteal_ratio)
                    attacker.hp = min(attacker.max_hp, attacker.hp + heal_amount)
                    msg += f"\n{attacker_name}は{heal_amount}回復した！"
                    # ライフスティール発動時も対象に赤色フラッシュ
                    if hasattr(target, "flash_color"):
                        target.flash_color = (255, 50, 50)
                    if hasattr(target, "damage_flash_timer"):
                        target.damage_flash_timer = max(target.damage_flash_timer, 60 + HIT_STUN_DURATION)
                    if _os.environ.get("DEBUG_MODE") == "1":
                        print(f"[ライフスティール] ✅ クリティカル発動")

    # --- カウンター効果（攻撃時に発動） ---
    if hasattr(target, "hp") and hasattr(attacker, "hp"):
        # targetがプレイヤーで、attackerが敵の場合のみカウンター発動
        # count_counter の合計が2以上で発動
        total_counter = getattr(target, "total_counter", 0)
        if isinstance(total_counter, int) and total_counter >= 2:
            proc_chance = getattr(target, "total_counter_proc_chance", 0.0)
            if isinstance(proc_chance, (int, float)) and proc_chance > 0:
                rolled = random.random()
                if _os.environ.get("DEBUG_MODE") == "1":
                    print(f"[カウンター] chance={proc_chance:.2%}, rolled={rolled:.4f} -> {'✅ 成功' if rolled < proc_chance else '❌ 失敗'}")
                if rolled < proc_chance:
                    counter_damage_ratio = getattr(target, "total_counter_damage_ratio", 0.5)
                    if isinstance(counter_damage_ratio, (int, float)) and counter_damage_ratio > 0:
                        # カウンター攻撃を実行（プレイヤーの攻撃力ベース）
                        counter_damage = int(getattr(target, "total_attack", target.attack) * counter_damage_ratio)
                        if hasattr(attacker, "take_damage"):
                            attacker.take_damage(counter_damage)
                        else:
                            attacker.hp = max(0, attacker.hp - counter_damage)
                        msg += f"\n{target_name}は反撃！{counter_damage}のダメージ！"
                        # プレイヤーが敵の方向いて攻撃モーションを再生
                        if (hasattr(target, "set_facing") and hasattr(target, "_perform_attack")
                                and hasattr(attacker, "x") and hasattr(attacker, "y")
                                and hasattr(target, "x") and hasattr(target, "y")
                                and not getattr(target, "is_falling", False)
                                and not getattr(target, "is_attacking", False)):
                            dx = attacker.x - target.x
                            dy = attacker.y - target.y
                            if abs(dx) > abs(dy):
                                target.set_facing("right" if dx > 0 else "left")
                            else:
                                target.set_facing("down" if dy > 0 else "up")
                            target._perform_attack()

    target_hp = getattr(target, 'hp', '?')
    target_cond = getattr(target, 'condition', 'normal')
    print(f"[COMBAT] {attacker_name} -> {target_name}: Damage={damage}, Critical={is_critical}, Miss={is_miss}, TargetHP: {target_hp}, TargetCond: {target_cond}")
    return counter_prefix + msg, damage, is_critical, False
