import pygame
import os

# Set dummy video driver to run headless
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((1, 1))

def draw_stone(color_name, filename):
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    base = pygame.Color(color_name)
    
    # Calculate shadow and highlight colors
    hsv = base.hsva
    shadow = pygame.Color(0, 0, 0)
    shadow.hsva = (hsv[0], min(100.0, hsv[1] + 10.0), max(0.0, hsv[2] - 35.0), hsv[3])
    highlight = pygame.Color(0, 0, 0)
    highlight.hsva = (hsv[0], max(0.0, hsv[1] - 30.0), min(100.0, hsv[2] + 35.0), hsv[3])
    
    # Left half shadow
    pygame.draw.polygon(surf, shadow, [(16, 4), (16, 28), (6, 16)])
    # Right half base
    pygame.draw.polygon(surf, base, [(16, 4), (26, 16), (16, 28)])
    # Top highlight facet
    pygame.draw.polygon(surf, highlight, [(16, 4), (21, 10), (16, 16), (11, 10)])
    
    # Draw a thin dark outline
    pygame.draw.polygon(surf, (20, 20, 20), [(16, 4), (26, 16), (16, 28), (6, 16)], 1)
    
    # Highlight cross lines
    pygame.draw.line(surf, highlight, (16, 4), (16, 28), 1)
    pygame.draw.line(surf, highlight, (6, 16), (26, 16), 1)

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    pygame.image.save(surf, filename)
    print(f"Generated icon: {filename}")

if __name__ == "__main__":
    icon_dir = "/Users/tj/Desktop/2DGame/components/pictures/icon"
    draw_stone("red", os.path.join(icon_dir, "red_stone.png"))
    draw_stone("blue", os.path.join(icon_dir, "blue_stone.png"))
    draw_stone("green", os.path.join(icon_dir, "green_stone.png"))
    draw_stone("purple", os.path.join(icon_dir, "purple_stone.png"))
