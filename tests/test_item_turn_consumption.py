import pygame
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# テストモードを強制して本番セーブデータを保護する
os.environ["TEST_MODE"] = "1"

from components.sprites.player import Player
from components.sprites.enemy import Enemy
from systems.dungeon import Dungeon
from systems.item_handler import make_use_item_callback
from wordings import Text

class MockDialog:
    def __init__(self):
        self.text = ""
        self.is_active = False

def test_item_use_consumes_turn():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    
    # テスト用データ
    player = Player()
    player.x, player.y = 100, 100
    player.hp = 50
    player.add_item_to_inventory("hp_potion")
    
    dungeon = Dungeon(level=1)
    # 敵を一人配置
    enemy = Enemy(200, 200, "slime")
    dungeon.enemies = [enemy]
    dialog = MockDialog()
    
    from systems.game_state import game_state
    game_state["turn_state"] = "player"
    game_state["item_action_active"] = False
    game_state["dialog_modal"] = False
    
    # アイテム使用コールバックの作成
    # 簡略化のため、ダミーのインベントリダイアログを作成
    class MockInventory:
        def __init__(self):
            self.is_active = True
            self.dungeon = dungeon
    
    inv = MockInventory()
    use_callback = make_use_item_callback(player, dialog, inv, game_state, dungeon=dungeon)
    
    print("--- アイテム使用ターン消費テスト ---")
    print(f"使用前: HP={player.hp}, enemy_turn_pending={getattr(player, 'enemy_turn_pending', False)}")
    
    # 1. ポーション使用
    use_callback("consumable", "hp_potion")
    
    print(f"使用後: HP={player.hp}, enemy_turn_pending={getattr(player, 'enemy_turn_pending', False)}")
    
    # 検証: HPが回復し、ターン消費フラグが立っていること
    assert player.hp > 50, "HPが回復していません"
    assert getattr(player, "enemy_turn_pending", False) == True, "アイテム使用後にターン消費フラグが立っていません"
    
    # 2. ターン遷移のシミュレーション
    # Player.update のロジックを模倣 (ダイアログが閉じている状態で update)
    dialog.is_active = False
    player.update(dungeon, dt=0, dialog=dialog)
    
    print(f"更新後: turn_state={game_state['turn_state']}, enemy_turn_pending={getattr(player, 'enemy_turn_pending', False)}")
    
    assert game_state["turn_state"] == "enemies", "敵のターンに遷移していません"
    assert getattr(player, "enemy_turn_pending", False) == False, "ターン開始後にフラグがリセットされていません"

    print("✅ アイテム使用ターン消費テスト合格！")

if __name__ == "__main__":
    try:
        test_item_use_consumes_turn()
        pygame.quit()
        sys.exit(0)
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)
