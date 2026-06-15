
import os
from constants import BGM_DEFEAT, BGM_VILLAGE
from wordings import Text
from systems.audio_manager import play_bgm

# 死亡演出のステップ定義:
# Step 0: 非アクティブ
# Step 1: フェードアウト中 (60f = 1秒)
# Step 2: 「力尽きた…」表示 (60f = 1秒)
# Step 3: 復活処理 → 病院ダイアログ
# Step 4: 病院ダイアログ閉じ待ち

FADE_DURATION = 60   # フェードアウトにかけるフレーム数
TEXT_DURATION  = 60  # 「力尽きた…」表示フレーム数

def handle_death_sequence(player, dungeon, dialog, game_state):
    """
    プレイヤー死亡時の演出シーケンス（タイマー、メッセージ、ペナルティ、復活）を処理する。
    """
    from systems.dungeon import warp_to_floor

    is_death_active = game_state.get("death_sequence_step", 0) > 0

    # Step 0: 死亡直後の検知と開始
    if player.is_dead and not is_death_active:
        play_bgm(BGM_DEFEAT)
        game_state["death_sequence_step"] = 1
        game_state["death_timer"] = FADE_DURATION
        game_state["death_fade_alpha"] = 0   # 暗転の不透明度 (0→255)
        is_death_active = True

    if not is_death_active:
        return dungeon

    step = game_state["death_sequence_step"]

    if step == 1:
        # フェードアウト中
        elapsed = FADE_DURATION - game_state["death_timer"]
        game_state["death_fade_alpha"] = int(255 * elapsed / FADE_DURATION)
        game_state["death_timer"] -= 1
        if game_state["death_timer"] <= 0:
            game_state["death_fade_alpha"] = 255
            game_state["death_sequence_step"] = 2
            game_state["death_timer"] = TEXT_DURATION

    elif step == 2:
        # 「力尽きた…」を表示しながら待機（入力無効）
        game_state["death_timer"] -= 1
        if game_state["death_timer"] <= 0:
            # Step 3: 復活処理
            player.apply_curse()
            player.hp = player.max_hp
            player.is_dead = False
            player.condition = "normal"
            player.status_timer = 0

            penalty = player.coin // 2
            player.coin -= penalty

            failed_quests = []
            for q in list(player.active_quests):
                failed_quests.append(q.get("title", "不明なクエスト"))
                player.remove_quest(q)

            dungeon = warp_to_floor(0, player, is_death=True, spawn_reason="continue")

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
            game_state["death_fade_alpha"] = 0  # 暗転解除
            game_state["death_sequence_step"] = 4

    elif step == 4:
        # 病院ダイアログが閉じられるのを待つ
        if not dialog.is_active:
            play_bgm(BGM_VILLAGE)
            game_state["death_sequence_step"] = 0

    return dungeon
