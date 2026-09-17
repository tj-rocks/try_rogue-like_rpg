import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["TEST_MODE"] = "1"
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.sprites.player import Player
from systems.item_handler import use_consumable
from wordings import Text


def _item_count(player, item_key):
    return sum(item["count"] for item in player.items if item["key"] == item_key)


def test_antidote_is_not_consumed_when_player_is_not_poisoned():
    player = Player()
    player.condition = "normal"
    player.add_item_to_inventory("antidote_potion", count=2)

    message = use_consumable("antidote_potion", player)

    assert message == Text.Items.ANTIDOTE_NOT_POISONED
    assert player.condition == "normal"
    assert _item_count(player, "antidote_potion") == 2


def test_antidote_cures_poison_and_consumes_one_item():
    player = Player()
    player.condition = "poison"
    player.add_item_to_inventory("antidote_potion", count=2)

    message = use_consumable("antidote_potion", player)

    assert message == Text.Items.ANTIDOTE_USE.format(name="毒消薬")
    assert player.condition == "normal"
    assert _item_count(player, "antidote_potion") == 1
