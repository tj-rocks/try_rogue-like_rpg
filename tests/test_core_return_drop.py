from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from components.sprites.enemy import Enemy
from components.sprites.player import Player
from systems.entity_handler import update_dungeon_entities
from systems.game_state import game_state


@pytest.mark.parametrize("layout", ["empty", "occupied_center", "full", "wall_center"])
def test_core_always_drops_return_wing_near_center_once(layout):
    saved_state = deepcopy(game_state)
    try:
        game_state["is_debug_mode"] = False
        player = Player()
        player.x = player.y = 0
        boss = Enemy(64, 64, "dungeon_core")
        boss.hp = 0
        boss.is_dead = True
        boss.damage_flash_timer = 0
        dungeon = MagicMock()
        dungeon.current_floor = 99
        dungeon.tile_size = 64
        dungeon.map_width = dungeon.map_height = 7
        dungeon.map_data = [[1] * 7 for _ in range(7)]
        dungeon.enemies = [boss]
        dungeon.dropped_items = []
        dungeon.magic_effects = []
        dungeon.traps = []
        if layout == "wall_center":
            dungeon.map_data[3][3] = 0
        positions = [(3, 3)] if layout == "occupied_center" else []
        if layout == "full":
            positions = [(x, y) for y in range(7) for x in range(7)]
        dungeon.dropped_items = [
            SimpleNamespace(x=x * 64, y=y * 64, is_collected=False)
            for x, y in positions
        ]
        with patch("systems.ui.show_dialog"), patch("systems.audio_manager.play_bgm"), patch.object(Enemy, "log_population"), patch("systems.entity_handler.random.random", return_value=0.999999), patch("constants.DROP_RATE_MULTIPLIER", 0.0):
            update_dungeon_entities(dungeon, player, 0.1, MagicMock())
            update_dungeon_entities(dungeon, player, 0.1, MagicMock())
        drops = [item for item in dungeon.dropped_items if getattr(item, "item_key", None) == "return_wing"]
        assert len(drops) == 1
        x, y = drops[0].x // 64, drops[0].y // 64
        if layout in ("occupied_center", "wall_center"):
            assert abs(x - 3) + abs(y - 3) == 1
        else:
            assert (x, y) == (3, 3)
        assert dungeon.enemies == []
    finally:
        game_state.clear()
        game_state.update(saved_state)
