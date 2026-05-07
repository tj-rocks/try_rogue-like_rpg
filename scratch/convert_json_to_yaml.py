import json
import yaml
import os

def convert_dir(target_dir):
    for filename in os.listdir(target_dir):
        if filename.endswith(".json"):
            json_path = os.path.join(target_dir, filename)
            yml_path = os.path.join(target_dir, filename.replace(".json", ".yml"))
            
            print(f"Converting {json_path} -> {yml_path}")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            with open(yml_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)

# 変換対象ディレクトリ
dirs = [
    "components/data/master",
    "components/data"
]

for d in dirs:
    if os.path.exists(d):
        convert_dir(d)
