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
        # 10x10の床。すべて 1 (床) で初期化
        self.map_data = [[1 for _ in range(10)] for _ in range(10)]

class MockDialog:
    pass

# Setup player
player = Player()
player.x, player.y = 64, 64  # grid (1, 1)
player.facing = "right"
player.name = "Hero"

dungeon = MockDungeon()

# Create Yrden Stave
stave = StaveInstance("yrden_stave", charges=5)

print("--- Test 1: Normal spawn in front (2, 1) ---")
# front is (2, 1) -> grid coords. x=128, y=64
msg = execute_stave(player, stave, dungeon, MockDialog())
print(msg)
print(f"Remaining charges (Expected 4): {stave.charges}")
print(f"Number of entities (Expected 1): {len(dungeon.enemies)}")
assert stave.charges == 4
assert len(dungeon.enemies) == 1
barrier = dungeon.enemies[0]
assert barrier.type == "magic_barrier"
assert barrier.is_static is True
print(f"Barrier spawned at grid: ({int(barrier.x//64)}, {int(barrier.y//64)})")

print("\n--- Test 2: Spawn when front is wall (3, 1) ---")
# Let's make (3, 1) a wall
dungeon.map_data[1][3] = 0  # wall
player.facing = "right"
# front of (2, 1) is (3, 1) (wall)
player.x, player.y = 128, 64  # move to (2, 1)
msg = execute_stave(player, stave, dungeon, MockDialog())
print(msg)
print(f"Remaining charges (Expected 4): {stave.charges}")
print(f"Number of entities (Expected 1): {len(dungeon.enemies)}")
assert stave.charges == 4  # Should not decrease
assert len(dungeon.enemies) == 1

print("\n--- Test 3: Spawn when front has enemy ---")
# restore (3, 1) to floor
dungeon.map_data[1][3] = 1
# Spawn enemy at (3, 1) -> x=192, y=64
enemy = Enemy(192, 64, "slime")
dungeon.enemies.append(enemy)
# Player is at (2, 1), facing right -> front is (3, 1) (occupied by enemy)
msg = execute_stave(player, stave, dungeon, MockDialog())
print(msg)
print(f"Remaining charges (Expected 3): {stave.charges}")
print(f"Number of entities (Expected 3): {len(dungeon.enemies)}")
assert stave.charges == 3  # Should decrease by 1
assert len(dungeon.enemies) == 3

# Verify that the enemy is trapped and cannot move
# Current position: (3, 1) -> x=192, y=64. Target: (4, 1) -> x=256, y=64
can_move_away = enemy.can_move_grid(256, 64, dungeon)
print(f"Trapped enemy can move to (4, 1): {can_move_away} (Expected False)")
assert can_move_away is False

# Verify that the trapped enemy passes its turn and does not attack the adjacent player
player.hp = 100
dialog = MockDialog()
dialog.text = ""
dialog.is_active = False
enemy.take_turn(player, dungeon, [player] + dungeon.enemies, dialog)
print(f"Trapped enemy took turn. Player HP: {player.hp} (Expected 100), Dialog text: '{dialog.text}' (Expected empty)")
assert player.hp == 100
assert dialog.text == ""


print("\n--- Test 4: Verify lifetime turns decrease and auto-destruct ---")
# Let's clear enemies and create a fresh barrier
dungeon.enemies = []
player.x, player.y = 64, 64  # Hero is at (1, 1)
player.facing = "right"
stave.charges = 5

# Normal spawn -> lifetime turns
msg = execute_stave(player, stave, dungeon, MockDialog())
print(msg)
assert len(dungeon.enemies) == 1
barrier = dungeon.enemies[0]
expected_turns = barrier.lifetime_turns
print(f"Barrier initial lifetime: {expected_turns}")

# Perform turns (each turn calling take_turn on all enemies)
for turn in range(1, expected_turns + 1):
    print(f"--- Turn {turn} passes ---")
    dialog = MockDialog()
    dialog.is_active = False
    dialog.text = ""
    # simulate entity handler taking turn
    for e in list(dungeon.enemies):
        e.take_turn(player, dungeon, [player] + dungeon.enemies, dialog)
        if getattr(e, "is_dead", False):
            dungeon.enemies.remove(e)
            print(f"Entity destroyed on turn {turn}! Msg: {dialog.text}")
    print(f"Active entities remaining: {len(dungeon.enemies)}")

assert len(dungeon.enemies) == 0
print("Lifetime and auto-destruction test passed!")

print("\n--- Test 5: Verify magic_yrden_turns bonus increases lifetime ---")
dungeon.enemies = []
stave.charges = 5

# Mock magic bonus on player
# player has get_magic_bonus method. Let's override it to return 3 for yrden_turns
player.get_magic_bonus = lambda key: 3 if key == "yrden_turns" else 0

msg = execute_stave(player, stave, dungeon, MockDialog())
print(msg)
assert len(dungeon.enemies) == 1
barrier = dungeon.enemies[0]
print(f"Barrier initial lifetime with +3 bonus (Expected {expected_turns + 3}): {barrier.lifetime_turns}")
assert barrier.lifetime_turns == expected_turns + 3

print("\nAll tests passed successfully!")
