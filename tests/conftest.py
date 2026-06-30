import os

import pygame
import pytest


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("TEST_MODE", "1")


@pytest.fixture(autouse=True)
def ensure_pygame_ready():
    if pygame.get_init():
        if not pygame.display.get_init():
            pygame.display.init()
    else:
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.init()
    if not pygame.display.get_surface():
        pygame.display.set_mode((1, 1))
    yield
    if pygame.display.get_init():
        pygame.display.quit()
    if pygame.get_init():
        pygame.quit()
