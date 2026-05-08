from PIL import Image
import os

def make_transparent(img_path, output_path):
    img = Image.open(img_path).convert("RGBA")
    datas = img.getdata()
    new_data = []
    for item in datas:
        # ピクセルアートなので、完全な白(255,255,255)に近い色を透明にする
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)
    img = img.resize((64, 64), Image.NEAREST)
    img.save(output_path)

mapping = {
    "apprentice_sprite_1777868075069.png": "apprentice",
    "guild_guide_sprite_1777868096217.png": "guild_guide",
    "dungeon_expert_sprite_1777868115180.png": "dungeon_expert",
    "guide_weapon_sprite_1777868139996.png": "guide_weapon",
    "guide_item_sprite_1777868161168.png": "guide_item",
    "guide_merchant_sprite_1777868187079.png": "guide_merchant",
    "guide_storage_sprite_1777868210538.png": "guide_storage",
    "guide_inn_sprite_1777868232976.png": "guide_inn",
    "guide_blacksmith_sprite_1777868261237.png": "guide_blacksmith",
    "guide_guild_q_sprite_1777868280703.png": "guide_guild",
    "guide_doctor_sprite_1777868305125.png": "guide_doctor",
    "guide_bank_sprite_1777868330112.png": "guide_bank"
}

brain_dir = "/Users/tj/.gemini/antigravity/brain/dcd6a06b-91f4-4353-9ea0-6ff2c23a00c5"
npc_dir = "components/pictures/npc"

for src_name, dst_folder in mapping.items():
    src_path = os.path.join(brain_dir, src_name)
    dst_path = os.path.join(npc_dir, dst_folder, "idel.png")
    if os.path.exists(src_path):
        make_transparent(src_path, dst_path)
        print(f"Processed {src_name} -> {dst_folder}/idel.png")
    else:
        print(f"File not found: {src_path}")
