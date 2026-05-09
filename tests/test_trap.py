import os
import sys
import pygame
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
pygame.init()
pygame.display.set_mode((100, 100))

from components.sprites.player import Player
from components.sprites.trap import Trap
from systems.dungeon import warp_to_floor
from systems.ui import Dialog

def test_poison_trap():
    print("--- 毒矢の罠テスト開始 ---")
    player = Player()
    # 1階へワープさせてダンジョン初期化
    dungeon = warp_to_floor(1, player, spawn_reason="test")
    
    # トラップのクリアとセットアップ
    dungeon.traps = []
    px, py = player.x // 64, player.y // 64
    
    # プレイヤーの足元に毒矢の罠を設置
    poison_trap = Trap(px, py, "poison_trap")
    dungeon.traps.append(poison_trap)
    
    # トラップの判定処理を実行
    dialog_mock = MagicMock()
    dungeon.check_traps(player, dialog_mock)
    
    # 検証: プレイヤーが毒状態になっているか
    print(f"プレイヤーの現在の状態: {player.condition}")
    assert player.condition == "poison", "プレイヤーが毒状態になっていません"
    
    # 検証: 描画時にクラッシュしないか (unhashable type: list などの確認)
    screen = pygame.Surface((100, 100))
    try:
        player.draw(screen, 0, 0)
        print("[OK] 毒状態での描画成功（クラッシュなし）")
    except Exception as e:
        assert False, f"毒状態の描画でエラーが発生しました: {e}"
        
    print("[OK] 毒矢の罠テスト合格！")

def test_damage_trap():
    print("--- 地雷の罠テスト開始 ---")
    player = Player()
    dungeon = warp_to_floor(1, player, spawn_reason="test")
    
    dungeon.traps = []
    px, py = player.x // 64, player.y // 64
    
    mine_trap = Trap(px, py, "mine")
    dungeon.traps.append(mine_trap)
    
    initial_hp = player.hp
    dialog_mock = MagicMock()
    dungeon.check_traps(player, dialog_mock)
    
    # 検証: HPが減少しているか
    print(f"初期HP: {initial_hp} -> 踏んだ後のHP: {player.hp}")
    assert player.hp < initial_hp, "地雷を踏んだのにHPが減っていません"
    
    # 地雷は踏むと消えるはず
    assert len(dungeon.traps) == 0, "地雷がマップから消去されていません"
    
    print("[OK] 地雷の罠テスト合格！")

if __name__ == "__main__":
    test_poison_trap()
    test_damage_trap()
