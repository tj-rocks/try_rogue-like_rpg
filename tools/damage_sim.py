import random

def simulate_damage():
    print("=== Rogue-like Damage Simulator ===")
    try:
        atk = int(input("Attacker ATK: ") or 10)
        dfn = int(input("Defender DEF: ") or 5)
        
        is_magic = input("Is Magic? (y/n): ").lower() == 'y'
        damage_mult = float(input("Damage Multiplier (default 1.0): ") or 1.0)
        
        accuracy = 100
        evasion = 0
        block_chance = 0.0
        is_back = False
        crit_rate_base = 0.01

        if not is_magic:
            accuracy = int(input("Attacker Accuracy (default 100): ") or 100)
            evasion = int(input("Defender Evasion (default 0): ") or 0)
            block_chance = float(input("Block Chance (0.0-1.0, default 0.0): ") or 0.0)
            is_back = input("Is Back Attack? (y/n): ").lower() == 'y'
            crit_rate_base = float(input("Base Crit Rate (0.01 = 1%, default 0.01): ") or 0.01)

        print("\n--- Simulation Settings ---")
        print(f"ATK: {atk}, DEF: {dfn}, Mult: {damage_mult}, Magic: {is_magic}")
        if not is_magic:
            print(f"Acc: {accuracy}, Eva: {evasion}, Block: {block_chance}, Back: {is_back}, CritBase: {crit_rate_base}")

        trials = 1000
        damages = []
        hits = 0
        crits = 0

        # Constants from the game (approximated)
        CRITICAL_RATE_MAX = 0.95

        for _ in range(trials):
            # 1. Hit check
            if is_magic:
                is_miss = False
            else:
                # Simplified hit rate logic
                hr = (accuracy - evasion) / 100.0
                if not is_back: # Frontal attack
                    hr -= block_chance
                hr = max(0.05, min(0.99, hr))
                is_miss = random.random() >= hr
            
            if is_miss:
                damages.append(0)
                continue
            
            hits += 1

            # 2. Critical check
            cr = crit_rate_base
            if is_back:
                cr += 0.25
            cr = min(CRITICAL_RATE_MAX, cr)
            
            is_critical = random.random() < cr
            if is_critical:
                crits += 1
            
            # 3. Damage calculation
            base_atk_val = int(atk * damage_mult)
            calc_atk = base_atk_val * 2 if is_critical else base_atk_val
            
            base_dmg = max(1, calc_atk - dfn)
            
            # Random variance: 80% to 100%
            final_dmg = int(base_dmg * (0.8 + random.uniform(0, 0.2)))
            final_dmg = max(1, final_dmg)
            
            damages.append(final_dmg)

        # Result Statistics
        actual_hits = [d for d in damages if d > 0]
        avg_dmg = sum(actual_hits) / len(actual_hits) if actual_hits else 0
        max_dmg = max(damages) if damages else 0
        min_dmg = min(actual_hits) if actual_hits else 0

        print("\n--- Results (1000 Trials) ---")
        print(f"Hit Rate: {hits/trials*100:.1f}%")
        print(f"Crit Rate (of hits): {crits/hits*100 if hits > 0 else 0:.1f}%")
        print(f"Avg Damage (if hit): {avg_dmg:.2f}")
        print(f"Min Damage (if hit): {min_dmg}")
        print(f"Max Damage: {max_dmg}")
        print(f"Total Expected Damage: {sum(damages)/trials:.2f} per turn")

    except ValueError:
        print("Invalid input. Please enter numbers.")

if __name__ == "__main__":
    simulate_damage()
