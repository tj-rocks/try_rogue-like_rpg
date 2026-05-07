import json
import os

save_path = "components/data/savefile/save_data.json"
if os.path.exists(save_path):
    with open(save_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # event_items を追加
    event_items = data.get("event_items", [])
    # すでにあるかチェック
    if not any(it["key"] == "guild_cert_e" for it in event_items):
        event_items.append({"key": "guild_cert_e", "count": 1})
    
    data["event_items"] = event_items
    
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Success: Added E-rank certificate to save data.")
else:
    print("Error: Save file not found.")
