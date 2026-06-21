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


class MockDialog:
    def __init__(self):
        self.text = ""
        self.is_active = False


def test_equip_change_consumes_turn():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))

    player = Player()
    player.x, player.y = 100, 100

    dungeon = Dungeon(level=1)
    enemy = Enemy(200, 200, "slime")
    dungeon.enemies = [enemy]
    dialog = MockDialog()

    from systems.game_state import game_state
    game_state["turn_state"] = "player"
    game_state["item_action_active"] = False
    game_state["dialog_modal"] = False

    class MockInventory:
        def __init__(self):
            self.is_active = True
            self.dungeon = dungeon

    inv = MockInventory()
    use_callback = make_use_item_callback(player, dialog, inv, game_state, dungeon=dungeon)

    print("--- 装備変更ターン消費テスト ---")

    # 武器を入手して装備
    weapon_inst = player.equip_weapon_by_key("iron_sword")
    assert weapon_inst is not None, "武器の装備に失敗しました"

    print(f"装備前: equipped_weapon={player.equipped_weapon}, enemy_turn_pending={getattr(player, 'enemy_turn_pending', False)}")

    use_callback("weapon", weapon_inst.iid)

    print(f"装備後: equipped_weapon={player.equipped_weapon}, enemy_turn_pending={getattr(player, 'enemy_turn_pending', False)}")

    # 検証: 装備が変更され、ターン消費フラグが立っていること
    assert player.equipped_weapon == weapon_inst.iid, "武器が装備されていません"
    assert getattr(player, "enemy_turn_pending", False) == True, "装備変更後にターン消費フラグが立っていません"

    # ターン遷移のシミュレーション
    dialog.is_active = False
    player.update(dungeon, dt=0, dialog=dialog)

    print(f"更新後: turn_state={game_state['turn_state']}, enemy_turn_pending={getattr(player, 'enemy_turn_pending', False)}")

    assert game_state["turn_state"] == "enemies", "敵のターンに遷移していません"
    assert getattr(player, "enemy_turn_pending", False) == False, "ターン開始後にフラグがリセットされていません"

    print("✅ 装備変更ターン消費テスト合格！")


if __name__ == "__main__":
    try:
        test_equip_change_consumes_turn()
        pygame.quit()
        sys.exit(0)
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)
