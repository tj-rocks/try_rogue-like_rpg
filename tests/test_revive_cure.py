import os
import sys
import pygame

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['TEST_MODE'] = '1'
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player

def test_revive_cure_poison():
    print("--- 復活時の状態異常回復テスト ---")
    player = Player()
    
    # 1. 毒状態にする
    player.condition = "poison"
    player.status_timer = 10
    print(f"状態セット: {player.condition}")
    
    # 2. 復活アイテムを持たせる
    player.items.append({"key": "revive_amulet", "count": 1})
    print(f"アイテム所持: {player.has_item('revive_amulet')}")
    
    # 3. 致命的なダメージを与える
    print("致命的ダメージ付与...")
    player.take_damage(999)
    
    # 4. 検証: 復活しているか
    print(f"生存確認: {not player.is_dead}, HP: {player.hp}")
    assert not player.is_dead
    assert player.hp > 0
    
    # 5. 検証: 毒が治っているか
    print(f"現在の状態: {player.condition}")
    assert player.condition == "normal"
    assert player.status_timer == 0
    
    print("✅ 復活時の状態異常回復テスト合格！")

if __name__ == "__main__":
    try:
        test_revive_cure_poison()
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        sys.exit(1)
