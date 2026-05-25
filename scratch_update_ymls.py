import os

files = [
    "components/data/master/weapons.yml",
    "components/data/master/armors.yml",
    "components/data/master/shields.yml"
]

for fpath in files:
    with open(fpath, "r") as f:
        lines = f.readlines()
    
    out = []
    for line in lines:
        out.append(line)
        if "stave_bonus:" in line and "light_stave_bonus:" not in line:
            # Find indentation
            indent = line[:len(line) - len(line.lstrip())]
            out.append(f"{indent}light_stave_bonus: 0\n")
            
    with open(fpath, "w") as f:
        f.writelines(out)

print("Updated YMLs successfully.")
