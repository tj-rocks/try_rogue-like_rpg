
import os
from constants import BGM_DEFEAT, BGM_VILLAGE
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
            
            # 死の呪いを進行させる
            player.apply_curse()

            player.hp = player.max_hp
            player.is_dead = False
            player.condition = "normal"
            player.status_timer = 0

            # 所持金を半分にする（借金にはならない）
            penalty = player.coin // 2
            player.coin -= penalty

            # 受注中のクエストをすべて失敗扱いにする
            failed_quests = []
            for q in list(player.active_quests):
                failed_quests.append(q.get("title", "不明なクエスト"))
                player.remove_quest(q)

            # 診療所へワープ
            dungeon = warp_to_floor(0, player, is_death=True, spawn_reason="continue")
            
            # [FIX] 絶望感を確定させるため、医者が話し始める前に即座にセーブする
            from systems.data_loader import SAVE_OFFICIAL_PATH
            player.save_to_file(SAVE_OFFICIAL_PATH)
            print(f"[DEATH] Progress saved with penalty to: {SAVE_OFFICIAL_PATH}")

            curse_msg = ""
            if player.curse_level > 0:
                curse_msg = f"\n\n🚨【死の呪い】段階 {player.curse_level}/5\n最大HPが {player.curse_level * 10}% 低下中"

            quest_msg = ""
            if failed_quests:
                quest_msg = "\n\n⚠【クエスト失敗】\n" + "\n".join(f"・{t}" for t in failed_quests)

            dialog.text = Text.System.DOCTOR_REVIVE.format(penalty=penalty) + curse_msg + quest_msg
            game_state["dialog_modal"] = True
            dialog.is_active = True
            game_state["death_sequence_step"] = 4
    
    elif step == 4:
        # 医者のメッセージが閉じられるのを待つ
        if not dialog.is_active:
            play_bgm(BGM_VILLAGE)
            game_state["death_sequence_step"] = 0
            
    return dungeon
