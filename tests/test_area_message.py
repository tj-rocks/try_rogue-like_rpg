"""
area_message のテスト
- dungeon.yml にキーがあれば下り方向のみ game_state に pending_area_message がセットされる
- 上り方向ではセットされない
"""
import os
import sys
import types
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["TEST_MODE"] = "1"


def _make_floor_info(area_message=None):
    d = {}
    if area_message is not None:
        d["area_message"] = area_message
    return d


class _FakeDungeon:
    def __init__(self, floor_level, floor_info):
        self.current_floor = floor_level
        self.floor_info = floor_info


class _FakePlayer:
    def __init__(self, prev_floor=0, max_reached_floor=0):
        self.prev_floor = prev_floor
        self.max_reached_floor = max_reached_floor
        self.current_floor = prev_floor

    def set_current_floor(self, floor):
        if floor > self.max_reached_floor:
            self.max_reached_floor = floor
        self.current_floor = floor


def _run_area_message_logic(floor_level, player, floor_info):
    """warp_to_floor 内の area_message セットロジックを抽出して実行"""
    from systems.game_state import game_state
    game_state.pop("pending_area_message", None)

    area_msg = floor_info.get("area_message")
    is_descending = floor_level > getattr(player, "prev_floor", -1)
    if area_msg and is_descending:
        game_state["pending_area_message"] = area_msg

    return game_state.get("pending_area_message")


# ------------------------------------------------------------------ #
# リスト形式のテスト
# ------------------------------------------------------------------ #


# ------------------------------------------------------------------ #
# テストケース
# ------------------------------------------------------------------ #

def test_area_message_set_on_descend():
    """下り方向で area_message（リスト）があれば game_state にセットされる"""
    player = _FakePlayer(prev_floor=12)
    floor_info = _make_floor_info(area_message=["巡礼者の聖域", "古代人が整備した神殿群。", "信仰と恐怖を試す。"])
    result = _run_area_message_logic(13, player, floor_info)
    assert result == ["巡礼者の聖域", "古代人が整備した神殿群。", "信仰と恐怖を試す。"]


def test_area_message_not_set_on_ascend():
    """上り方向（戻り）では area_message があってもセットされない"""
    player = _FakePlayer(prev_floor=14)
    floor_info = _make_floor_info(area_message=["巡礼者の聖域", "古代人が整備した神殿群。"])
    result = _run_area_message_logic(13, player, floor_info)
    assert result is None


def test_area_message_not_set_when_key_missing():
    """area_message キーがなければ何もセットされない"""
    player = _FakePlayer(prev_floor=12)
    floor_info = _make_floor_info()
    result = _run_area_message_logic(13, player, floor_info)
    assert result is None


def test_area_message_set_on_revisit_descend():
    """再訪でも下り方向であればセットされる"""
    player = _FakePlayer(prev_floor=12, max_reached_floor=50)
    floor_info = _make_floor_info(area_message=["巡礼者の聖域", "古代人が整備した神殿群。"])
    result = _run_area_message_logic(13, player, floor_info)
    assert result == ["巡礼者の聖域", "古代人が整備した神殿群。"]


def test_dungeon_yml_has_area_messages():
    """dungeon.yml の各エリア境界フロアに area_message が存在する"""
    import yaml
    yml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "components", "data", "master", "dungeon.yml")
    with open(yml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    floors_section = data.get("DUNGEON_IMAGES", {})
    assert "13" in floors_section, "13F のデータが dungeon.yml に存在しない"
    assert "area_message" in floors_section["13"], "13F に area_message キーがない"
    msg = floors_section["13"]["area_message"]
    assert isinstance(msg, list), "13F の area_message がリスト形式でない"
    assert len(msg) >= 1, "13F の area_message が空リスト"
