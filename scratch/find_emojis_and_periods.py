import os
import re

emoji_pattern = re.compile(
    r'[\u2600-\u27BF]|'
    r'[\u200D\uFE0F]|'  # Zero Width Joiner and Variation Selector
    r'[\uD83C-\uDBFF\uDC00-\uDFFF]', # Surrogate pairs for U+1F000 and above
    re.UNICODE
)

def contains_emoji(text):
    return bool(emoji_pattern.search(text))

def main():
    root_dir = '/Users/tj/Desktop/2DGame'
    target_files = []
    for root, dirs, files in os.walk(root_dir):
        if any(p in root for p in ['venv', '.git', '.github', '__pycache__', 'scratch', 'tests']):
            continue
        for file in files:
            if file.endswith('.yml') or file.endswith('.yaml') or file == 'wordings.py' or file == 'ui.py':
                target_files.append(os.path.join(root, file))

    print("=== TARGET FILES ===")
    for path in target_files:
        print(path)

    print("\n=== EMOJIS FOUND IN TARGET FILES ===")
    for filepath in target_files:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for idx, line in enumerate(f, 1):
                if contains_emoji(line):
                    emojis = [c for c in line if emoji_pattern.search(c) or ord(c) > 0xFFFF]
                    print(f"{os.path.basename(filepath)}:L{idx}: {line.strip()} (emojis: {emojis})")

    print("\n=== PERIODS FOUND IN TARGET FILES ===")
    for filepath in target_files:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for idx, line in enumerate(f, 1):
                if '。' in line:
                    print(f"{os.path.basename(filepath)}:L{idx}: {line.strip()}")

if __name__ == '__main__':
    main()
