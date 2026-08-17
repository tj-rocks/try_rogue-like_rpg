
import os
import sys
import pygame
from unittest.mock import MagicMock, patch

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pygameの初期化
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["TEST_MODE"] = "1"
pygame.init()
pygame.display.set_mode((1, 1))

from components.sprites.player import Player
from constants import WEAPON_DATA, ARMOR_DATA, SHIELD_DATA


def test_normal_stock_only_fixed_rank():
    """通常時: そのランク以下で最も高いランクの固定品のみ並ぶ"""
    print("--- 通常時ショップ固定品テスト開始 ---")

    from systems.dungeon import warp_to_floor

    # ギルド未所属でも序盤用のFランク装備は販売される
    unranked_player = Player()
    unranked_player.guild_rank = "-"
    unranked_dungeon = warp_to_floor(0, unranked_player, spawn_reason="test")
    unranked_stock = unranked_dungeon.weapon_shop_stock
    assert unranked_stock, "未所属ランクの武器屋在庫が空です"
    for stock in unranked_stock:
        data = {**WEAPON_DATA, **ARMOR_DATA, **SHIELD_DATA}[stock["key"]]
        assert data.get("min_rank", "F") == "F", f"未所属ランクでF以外の商品が販売されています: {stock['key']}"

    # Fランクプレイヤー
    player = Player()
    player.guild_rank = "F"
    player.coin = 99999
    dungeon = warp_to_floor(0, player, spawn_reason="test")

    # 全データを結合して参照
    ALL_DATA = {**WEAPON_DATA, **ARMOR_DATA, **SHIELD_DATA}

    # 武器屋の在庫確認: Fランク固定品のみ
    weapon_keys = [s["key"] for s in dungeon.weapon_shop_stock]
    print(f"  Fランク武器屋在庫: {weapon_keys}")

    # shop.usually_buyable を持つ品のみが並ぶ
    for s in dungeon.weapon_shop_stock:
        data = ALL_DATA.get(s["key"], {})
        shop = data.get("shop", {})
        assert shop.get("usually_buyable", False), f"非固定品 {s['key']} が通常在庫に含まれている"
        print(f"  [OK] {s['key']} (min_rank={data.get('min_rank')}, usually_buyable={shop.get('usually_buyable')})")

    # Dランクプレイヤー
    player.guild_rank = "D"
    dungeon = warp_to_floor(0, player, spawn_reason="test")
    weapon_keys = [s["key"] for s in dungeon.weapon_shop_stock]
    print(f"  Dランク武器屋在庫: {weapon_keys}")

    # Dランク以下で最も高いランクの固定品が並ぶ
    for s in dungeon.weapon_shop_stock:
        data = ALL_DATA.get(s["key"], {})
        shop = data.get("shop", {})
        assert shop.get("usually_buyable", False), f"非固定品 {s['key']} が通常在庫に含まれている"

    print("[OK] 通常時ショップ固定品テスト合格！")


def test_mission_bonus_unlocks_all_buyable():
    """ミッション達成後: shop_buyable: trueの全品が解禁される"""
    print("--- ミッション後全品解禁テスト開始 ---")

    from systems.dungeon import warp_to_floor

    player = Player()
    player.guild_rank = "D"
    player.coin = 99999
    player.shop_bonus_refresh = True  # ミッション達成フラグ

    dungeon = warp_to_floor(0, player, spawn_reason="test")

    weapon_keys = [s["key"] for s in dungeon.weapon_shop_stock]
    print(f"  ミッション後武器屋在庫: {weapon_keys}")

    # shop.special_buyable: true かつ min_rank <= D の全品が含まれる
    expected_keys = [
        k for k, v in WEAPON_DATA.items()
        if v.get("shop", {}).get("special_buyable", False) and v.get("min_rank", "F") in ("F", "E", "D")
    ]
    for ek in expected_keys:
        assert ek in weapon_keys, f"shop_buyable品 {ek} がミッション後在庫に含まれていない"
        print(f"  [OK] {ek} が在庫にある")

    # リミット30以下
    assert len(dungeon.weapon_shop_stock) <= 30, f"在庫が30を超えている: {len(dungeon.weapon_shop_stock)}"

    # フラグがリセットされている
    assert player.shop_bonus_refresh == False, "shop_bonus_refreshがリセットされていない"

    print("[OK] ミッション後全品解禁テスト合格！")


def test_a_rank_never_in_shop():
    """Aランク品(shop_buyable: false)はミッション後でもショップに出ない"""
    print("--- Aランク品非表示テスト開始 ---")

    from systems.dungeon import warp_to_floor

    player = Player()
    player.guild_rank = "A"
    player.coin = 99999
    player.shop_bonus_refresh = True

    dungeon = warp_to_floor(0, player, spawn_reason="test")

    weapon_keys = [s["key"] for s in dungeon.weapon_shop_stock]

    # shop.special_buyable: false のアイテムは絶対出ない
    for k, v in WEAPON_DATA.items():
        if not v.get("shop", {}).get("special_buyable", False):
            assert k not in weapon_keys, f"special_buyable:false の {k} がショップに出ている"

    print("[OK] Aランク品非表示テスト合格！")


def test_stock_limit_30():
    """ミッション後の在庫はリミット30を超えない"""
    print("--- 在庫リミット30テスト開始 ---")

    from systems.dungeon import warp_to_floor

    player = Player()
    player.guild_rank = "D"
    player.coin = 99999
    player.shop_bonus_refresh = True

    dungeon = warp_to_floor(0, player, spawn_reason="test")

    all_stocks = [
        ("武器屋", dungeon.weapon_shop_stock),
        ("防具専門店", dungeon.dedicated_armor_shop_stock),
        ("武器専門店", dungeon.dedicated_weapon_shop_stock),
        ("アクセサリ専門店", dungeon.dedicated_accessory_shop_stock),
    ]
    for name, stock in all_stocks:
        assert len(stock) <= 30, f"{name}の在庫が30を超えている: {len(stock)}"
        print(f"  [OK] {name}: {len(stock)}品 (<= 30)")

    print("[OK] 在庫リミット30テスト合格！")


if __name__ == "__main__":
    try:
        test_normal_stock_only_fixed_rank()
        test_mission_bonus_unlocks_all_buyable()
        test_a_rank_never_in_shop()
        test_stock_limit_30()
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
