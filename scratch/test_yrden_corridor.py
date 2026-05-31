import pygame
pygame.init()
pygame.display.set_mode((100, 100))

from components.sprites.player import Player, StaveInstance
from systems.magic_handler import execute_stave

class MockDungeon:
    def __init__(self):
        self.enemies = []
        self.magic_effects = []
        self.tile_size = 64
        self.map_width = 10
        self.map_height = 10
        # Initialize as 0 (wall)
        self.map_data = [[0 for _ in range(10)] for _ in range(10)]

class MockDialog:
    pass

def test_yrden_corridor_placement():
    player = Player()
    player.x, player.y = 64, 64  # (1, 1)
    player.facing = "right"
    player.name = "Hero"
    
    stave = StaveInstance("yrden_stave", charges=5)
    
    # 1. Test corridor value 4
    dungeon = MockDungeon()
    dungeon.map_data[1][1] = 4  # Player's tile is corridor
    dungeon.map_data[1][2] = 4  # Target tile (2, 1) is corridor
    
    msg = execute_stave(player, stave, dungeon, MockDialog())
    print(f"Placing on corridor (4): {msg}")
    assert len(dungeon.enemies) == 1
    assert dungeon.enemies[0].type == "magic_barrier"
    print("✅ Corridor (4) placement test passed!")

    # 2. Test corridor value 5
    stave.charges = 5
    dungeon = MockDungeon()
    dungeon.map_data[1][1] = 5
    dungeon.map_data[1][2] = 5
    
    msg = execute_stave(player, stave, dungeon, MockDialog())
    print(f"Placing on corridor (5): {msg}")
    assert len(dungeon.enemies) == 1
    assert dungeon.enemies[0].type == "magic_barrier"
    print("✅ Corridor (5) placement test passed!")

    # 3. Test corridor value 6
    stave.charges = 5
    dungeon = MockDungeon()
    dungeon.map_data[1][1] = 6
    dungeon.map_data[1][2] = 6
    
    msg = execute_stave(player, stave, dungeon, MockDialog())
    print(f"Placing on corridor (6): {msg}")
    assert len(dungeon.enemies) == 1
    assert dungeon.enemies[0].type == "magic_barrier"
    print("✅ Corridor (6) placement test passed!")

    print("🎉 All corridor Yrden placement tests passed successfully!")

if __name__ == "__main__":
    test_yrden_corridor_placement()
