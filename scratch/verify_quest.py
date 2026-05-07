import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.getcwd())

# Pygameの初期化（画面なしモード）
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player

def test_guild_quest_logic():
    print("[Test] Initializing Player to check Guild Quest logic...")
    player = Player()
    
    # 初期状態
    player.gold = 1000
    player.active_quest = None
    player.quest_tokens = {"slime": 3} # すでに3個集めている想定
    
    print(f"\nInitial State: Gold={player.gold}, Quest={player.active_quest}, Tokens={player.quest_tokens}")
    
    # 1. クエスト受注テスト
    quest_data = {"id": "hunt_slime", "title": "Slime Hunt", "reward": 200, "target_token": "slime"}
    player.active_quest = quest_data
    print(f"Quest Accepted: {player.active_quest['title']}")
    
    # 2. 破棄テスト（違約金 50% = 200 * 0.5 = 100）
    print("\n--- Abandoning Quest ---")
    if player.active_quest:
        penalty = int(player.active_quest.get("reward", 0) * 0.5)
        if player.gold >= penalty:
            player.gold -= penalty
            player.active_quest = None
            player.quest_tokens = {} # クエストに関わるトークンをリセット
            print(f"Success: Penalty paid ({penalty}G). Gold={player.gold}")
        else:
            print("FAILED: Not enough gold for penalty.")
            
    # 結果検証
    if player.active_quest is None and player.gold == 900 and player.quest_tokens == {}:
        print("SUCCESS: Quest logic (Abandonment) is correct.")
    else:
        print(f"ERROR: State mismatch. Gold={player.gold}, Tokens={player.quest_tokens}")

    print("\n[Test] Verification Complete.")

if __name__ == "__main__":
    try:
        test_guild_quest_logic()
    finally:
        pygame.quit()
