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

    def line(text, y, size=28, color=(235, 235, 220), center_x=600):
        font = pygame.font.Font(font_path, size)
        surface = font.render(text, True, color)
        rect = surface.get_rect(midtop=(center_x, y))
        assert canvas.get_rect().contains(rect), text
        canvas.blit(surface, rect)

    line("CREDITS", 54, 48)
    line("PM / QA : Yasutoki Iwasaki", 143)
    line("開発：Taiji Iwasaki", 185)
    line("Test / Debug : Harunobu Iwasaki", 227)
    groups = [
        (320, 332, "Graphics / Textures", ["ShareTextures", "ぴぽや", "Original graphics & photography"]),
        (320, 494, "Sound Effects", ["効果音ラボ"]),
        (320, 602, "Music", ["Suno"]),
        (880, 332, "AI-Generated Graphics", ["OpenAI ChatGPT", "Google Gemini"]),
        (880, 494, "Development Support", ["OpenAI ChatGPT", "OpenAI Codex", "Google Gemini"]),
    ]
    for center_x, y, heading, names in groups:
        line(heading, y, 24, (150, 150, 150), center_x=center_x)
        for index, name in enumerate(names):
            line(name, y + 38 + index * 34, 26, center_x=center_x)
    line("Thanks for playing.", 757, 32)
    line("This game is distributed free of charge and is not monetized.", 823, 22, (150, 150, 150))
    pygame.image.save(canvas, "components/pictures/ending/credits.png")
    pygame.font.quit()


if __name__ == "__main__":
    main()
