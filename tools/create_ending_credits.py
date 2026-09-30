"""既存フォントで最終クレジット画像を生成する。リポジトリ直下で実行。"""
from pathlib import Path

import pygame
import yaml


def main():
    pygame.font.init()
    config = yaml.safe_load(Path("components/data/master/ui.yml").read_text())
    font_path = config["font"]["path"]
    canvas = pygame.Surface((1200, 900))
    canvas.fill((0, 0, 0))

    def line(text, y, size=28, color=(235, 235, 220)):
        font = pygame.font.Font(font_path, size)
        surface = font.render(text, True, color)
        rect = surface.get_rect(midtop=(600, y))
        assert canvas.get_rect().contains(rect), text
        canvas.blit(surface, rect)

    line("CREDITS", 54, 48)
    groups = [
        (145, "Graphics / Textures", ["ShareTextures", "ぴぽや", "Original graphics & photography"]),
        (293, "Sound Effects", ["効果音ラボ"]),
        (377, "Music", ["Suno"]),
        (461, "AI-Generated Graphics", ["OpenAI ChatGPT", "Google Gemini"]),
        (577, "Development Support", ["OpenAI ChatGPT", "OpenAI Codex", "Google Gemini"]),
    ]
    for y, heading, names in groups:
        line(heading, y, 24, (150, 150, 150))
        for index, name in enumerate(names):
            line(name, y + 34 + index * 32)
    line("Thanks for playing.", 757, 32)
    line("This game is distributed free of charge and is not monetized.", 823, 22, (150, 150, 150))
    pygame.image.save(canvas, "components/pictures/ending/credits.png")
    pygame.font.quit()


if __name__ == "__main__":
    main()
