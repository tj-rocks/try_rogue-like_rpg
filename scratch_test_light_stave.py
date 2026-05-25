import pygame
pygame.init()
pygame.display.set_mode((100, 100))

from components.sprites.player import Player, StaveInstance
from components.sprites.enemy import Enemy
from systems.magic_handler import execute_stave

class MockDungeon:
    def __init__(self):
        self.enemies = []
        self.magic_effects = []
        self.tile_size = 64
        self.map_width = 10
        self.map_height = 10
    def reveal_floor(self):
        print("[MockDungeon] Floor revealed!")

class MockDialog:
    pass

player = Player()
player.x, player.y = 0, 0
player.facing = "right"
player.name = "Hero"

dungeon = MockDungeon()
# Create some enemies
slime = Enemy(0, 0, "slime")
goblin = Enemy(0, 0, "goblin")
dungeon.enemies = [slime, goblin]

# Store original detect ranges
slime_orig_detect = slime.detect_range
goblin_orig_detect = goblin.detect_range
print(f"Original Slime detect: {slime_orig_detect}")
print(f"Original Goblin detect: {goblin_orig_detect}")

# Create Light Stave +0
stave = StaveInstance("light_stave", charges=1)
stave.enhance = 0

msg = execute_stave(player, stave, dungeon, MockDialog())
print(f"--- Stave +0 Used ---")
print(msg)
print(f"Slime detect (Expected {slime_orig_detect}): {slime.detect_range}")
print(f"Goblin detect (Expected {goblin_orig_detect}): {goblin.detect_range}")
assert slime.detect_range == slime_orig_detect
assert goblin.detect_range == goblin_orig_detect

# Reset charges and upgrade to +10
stave.charges = 1
stave.enhance = 10

msg = execute_stave(player, stave, dungeon, MockDialog())
print(f"--- Stave +10 Used ---")
print(msg)
print(f"Slime detect (Expected {max(1, slime_orig_detect - 5)}): {slime.detect_range}")
print(f"Goblin detect (Expected {max(1, goblin_orig_detect - 5)}): {goblin.detect_range}")
assert slime.detect_range == max(1, slime_orig_detect - 5.0)
assert goblin.detect_range == max(1, goblin_orig_detect - 5.0)

print("Tests passed!")
