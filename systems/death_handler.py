
import os
from constants import (
    BGM_DEFEAT, BGM_VILLAGE, PLAYER_DEFENSE, DOCTOR_FEE
)
from wordings import Text
from systems.audio_manager import play_bgm

def handle_death_sequence(player, dungeon, dialog, game_state):
    """
    プレイヤー死亡時の演出シーケンス（タイマー、メッセージ、ペナルティ、復活）を処理する。
    main.py から抽出されたロジック。
    """
    from systems.dungeon import warp_to_floor

    is_death_active = game_state.get("death_sequence_step", 0) > 0
    
    # Step 0: 死亡直後の検知と開始
    if player.is_dead and not is_death_active:
        play_bgm(BGM_DEFEAT)
        game_state["death_sequence_step"] = 1
        game_state["death_timer"] = 60 # 1秒待機
        is_death_active = True
        
    if not is_death_active:
        return dungeon

    step = game_state["death_sequence_step"]
    
    if step == 1:
        game_state["death_timer"] -= 1
        if game_state["death_timer"] <= 0:
            # Step 2: 死亡メッセージ表示
            dialog.text = Text.System.GAME_OVER
            game_state["dialog_modal"] = True # 必ずキー入力を待つ
            dialog.is_active = True
            game_state["death_sequence_step"] = 2
    
    elif step == 2:
        # メッセージが閉じられるのを待つ
        if not dialog.is_active:
            game_state["death_sequence_step"] = 3
            game_state["death_timer"] = 60 # さらに1秒待機
    
    elif step == 3:
        game_state["death_timer"] -= 1
        if game_state["death_timer"] <= 0:
            # Step 4: 復活処理（ペナルティ適用とワープ）
            player.items = []
            player.weapon_inventory = []
            player.armor_inventory = []
            player.shield_inventory = []
            player.stave_inventory = []
            player.lantern_inventory = []
            player.equipped_weapon = None
            player.equipped_armor = None
            player.equipped_shield = None
            player.equipped_lantern = None
            player.weapon = None
            player.defense = PLAYER_DEFENSE
            player.block_chance = 0.0
            player.hp = player.max_hp
            player.is_dead = False
            
            # 復活時の最低限の装備（木の棍棒）を再付与
            player.equip_weapon_by_key("wooden_stick")

            # 所持金を半分にする（銀行預金は無事）
            player.coin //= 2
            
            # 医者の治療費を適用（優先度：手持ち -> 銀行 -> 借金）
            fee = DOCTOR_FEE
            if player.coin >= fee:
                player.coin -= fee
            else:
                fee -= player.coin
                player.coin = 0
                if player.bank_coin >= fee:
                    player.bank_coin -= fee
                else:
                    # 銀行にも足りなければ借金（マイナス）
                    fee -= player.bank_coin
                    player.bank_coin = 0
                    player.coin = -fee

            # 診療所へワープ
            dungeon = warp_to_floor(0, player, spawn_reason="continue")
            
            # [FIX] 絶望感を確定させるため、医者が話し始める前に即座にセーブする
            from systems.data_loader import SAVE_OFFICIAL_PATH
            player.save_to_file(SAVE_OFFICIAL_PATH)
            print(f"[DEATH] Progress saved with penalty to: {SAVE_OFFICIAL_PATH}")

            dialog.text = Text.System.DOCTOR_REVIVE
            game_state["dialog_modal"] = True
            dialog.is_active = True
            game_state["death_sequence_step"] = 4
    
    elif step == 4:
        # 医者のメッセージが閉じられるのを待つ
        if not dialog.is_active:
            play_bgm(BGM_VILLAGE)
            game_state["death_sequence_step"] = 0
            
    return dungeon
