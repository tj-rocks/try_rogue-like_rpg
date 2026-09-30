from types import SimpleNamespace
from unittest.mock import patch

import pytest

from components.sprites.enemy import Enemy


@pytest.mark.parametrize("floor,close,ranged", [
    (1, 0.70, 0.60),
    (49, 0.70, 0.60),
    (50, 0.704838710, 0.606451613),
    (60, 0.753225806, 0.670967742),
    (70, 0.801612903, 0.735483871),
    (79, 0.845161290, 0.793548387),
    (80, 0.85, 0.80),
    (81, 0.85, 0.80),
    (98, 0.85, 0.80),
    (99, 1.0, 1.0),
    (100, 0.85, 0.80),
])
@pytest.mark.parametrize("attack_type", ["close", "ranged"])
@pytest.mark.parametrize("enemy_type,distance", [("slime", 2), ("dungeon_core", 2), ("dungeon_core", 3)])
def test_enemy_attack_multiplier_by_floor(floor, close, ranged, attack_type, enemy_type, distance):
    enemy = Enemy(0, 0, "slime")
    enemy.current_attack_mode = "line"
    enemy.attack_effects = {"line": "test_attack"}
    enemy.current_attack_distance = distance
    enemy.type = enemy_type
    player = SimpleNamespace(x=64, y=0, width=64, height=64)
    dungeon = SimpleNamespace(current_floor=floor, tile_size=64)

    with patch.dict("constants.ATTACK_EFFECT_DATA", {"test_attack": {"type": attack_type}}), patch("systems.sound_handler.sound_manager.play_sfx"):
        enemy._execute_actual_attack(player, dungeon, None)

    expected = close if attack_type == "close" else ranged
    if enemy_type == "dungeon_core" and distance == 2:
        expected *= 2 / 3
    assert enemy.current_attack_damage_mult == pytest.approx(expected)
