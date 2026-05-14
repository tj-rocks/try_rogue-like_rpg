import hashlib
import os

files = [
    "almost_there.mp3",
    "beyond_the_suffer.mp3",
    "deep_floors.mp3",
    "deep_floors2.mp3",
    "gameover.mp3",
    "get_hornor.mp3",
    "goto_unknown_area.mp3",
    "just_move.mp3",
    "lost_my_mind.mp3",
    "middle_1.mp3",
    "middle_2.mp3",
    "need_more_adventures.mp3",
    "step_into_adventure.mp3",
    "step_into_next_floor.mp3",
    "turning_point.mp3",
    "village_theme.mp3",
    "where_is_hopes.mp3",
    "winding_adventure.mp3"
]

base_dir = "components/sounds/bgm/"
hashes = {}

print("--- BGM Duplicate Check ---")

for filename in files:
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        print(f"[Skip] {filename} (File not found)")
        continue
        
    # Calculate MD5 hash
    hasher = hashlib.md5()
    with open(path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    file_hash = hasher.hexdigest()
    
    if file_hash in hashes:
        hashes[file_hash].append(filename)
    else:
        hashes[file_hash] = [filename]

# Report duplicates
found_duplicates = False
for h, filenames in hashes.items():
    if len(filenames) > 1:
        found_duplicates = True
        print(f"\n[Duplicate Found] Hash: {h}")
        for f in filenames:
            size = os.path.getsize(os.path.join(base_dir, f))
            print(f"  - {f} ({size} bytes)")

if not found_duplicates:
    print("\nNo identical files found.")
