import os
import unicodedata

def is_standard_japanese_or_latin(c):
    o = ord(c)
    # ASCII / Standard Latin
    if o <= 0x7E:
        return True
    
    # Common Latin extensions / control / smart quotes
    if o in [0x2018, 0x2019, 0x201C, 0x201D, 0x2026, 0x2212, 0x00D7, 0x00F7]: # ‘ ’ “ ” … − × ÷
        return True
    
    # Hiragana: 3040-309F
    if 0x3040 <= o <= 0x309F:
        return True
        
    # Katakana: 30A0-30FF
    if 0x30A0 <= o <= 0x30FF:
        return True
        
    # Kanji (CJK Unified Ideographs): 4E00-9FFF
    if 0x4E00 <= o <= 0x9FFF:
        return True
        
    # CJK Symbols and Punctuation (e.g., 、 。 「 」 『 』 〜 〃 〒 々 〇)
    if 0x3000 <= o <= 0x303F:
        return True
        
    # Full-width forms (Full-width alphanumeric, Katakana half-width, etc.)
    if 0xFF00 <= o <= 0xFFEF:
        return True
        
    # Full-width Hiragana/Katakana variations
    if 0x30F0 <= o <= 0x30F7:
        return True

    # CJK Compatibility Ideographs
    if 0xF900 <= o <= 0xFAFF:
        return True

    return False

def main():
    root_dir = '/Users/tj/Desktop/2DGame'
    target_files = []
    for root, dirs, files in os.walk(root_dir):
        if any(p in root for p in ['venv', '.git', '.github', '__pycache__', 'scratch', 'tests']):
            continue
        for file in files:
            if file.endswith('.yml') or file.endswith('.yaml') or file == 'wordings.py' or file == 'ui.py':
                target_files.append(os.path.join(root, file))

    print("=== NON-STANDARD SYMBOLS FOUND ===")
    all_non_std = {}
    for filepath in target_files:
        rel_path = os.path.relpath(filepath, root_dir)
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for idx, line in enumerate(f, 1):
                non_std_in_line = []
                for c in line:
                    if not is_standard_japanese_or_latin(c) and not c.isspace():
                        non_std_in_line.append(c)
                if non_std_in_line:
                    print(f"{rel_path}:L{idx}: {line.strip()} | Symbols: {list(set(non_std_in_line))}")
                    for s in non_std_in_line:
                        all_non_std[s] = all_non_std.get(s, 0) + 1

    print("\n=== SUMMARY OF SYMBOLS ===")
    for s, count in sorted(all_non_std.items(), key=lambda x: x[1], reverse=True):
        print(f"Char: {s} | Unicode: U+{ord(s):04X} | Count: {count} | Name: {unicodedata.name(s, 'UNKNOWN')}")

if __name__ == '__main__':
    main()
