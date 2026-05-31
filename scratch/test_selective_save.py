import os
import sys
import yaml
import shutil
import time
import subprocess
import urllib.request
import json

ENEMIES_YML = "/Users/tj/Desktop/2DGame/components/data/master/enemies.yml"
BACKUP_YML = ENEMIES_YML + ".bak"

def test_selective_save():
    # 1. Back up the original enemies.yml
    print("Backing up enemies.yml...")
    shutil.copyfile(ENEMIES_YML, BACKUP_YML)

    server_process = None
    try:
        # Load current values
        with open(ENEMIES_YML, "r", encoding="utf-8") as f:
            original_data = yaml.safe_load(f) or {}
        
        orig_slime_hp = original_data["ENEMY_DATA"]["slime"]["hp"]
        orig_skeleton_hp = original_data["ENEMY_DATA"]["skeleton"]["hp"]
        print(f"Original stats - slime HP: {orig_slime_hp}, skeleton HP: {orig_skeleton_hp}")

        # 2. Start the auto_balancer server in the background
        print("Starting auto_balancer server...")
        server_process = subprocess.Popen(
            [sys.executable, "/Users/tj/Desktop/2DGame/tools/オートバランス調整.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a bit for the server to spin up
        time.sleep(2)

        # 3. Simulate the payload from the frontend for rank D only
        # (This simulates having selected rank D and clicked Apply to YAML)
        payload = {
            "enemies": {
                "skeleton": {
                    "hp": 999,
                    "attack": 88,
                    "defense": 77,
                    "evasion": 66,
                    "accuracy_close": 55
                }
                # note: slime (rank F) is NOT in this payload, representing rank-selective saving
            }
        }

        # 4. Make the POST request to the API
        url = "http://localhost:5010/api/auto-apply"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        print("Sending POST request to /api/auto-apply...")
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            print(f"Server response: {res_data}")
            assert res_data.get("status") == "success"

        # 5. Reload and check enemies.yml
        with open(ENEMIES_YML, "r", encoding="utf-8") as f:
            updated_data = yaml.safe_load(f) or {}

        updated_slime = updated_data["ENEMY_DATA"]["slime"]
        updated_skeleton = updated_data["ENEMY_DATA"]["skeleton"]

        print(f"Updated stats - slime HP: {updated_slime['hp']}, skeleton HP: {updated_skeleton['hp']}")

        # Assertions
        assert updated_slime["hp"] == orig_slime_hp, "Error: Rank F enemy (slime) was modified when it shouldn't have been!"
        assert updated_skeleton["hp"] == 999, "Error: Rank D enemy (skeleton) was not updated successfully!"
        assert updated_skeleton["attack"] == 88
        assert updated_skeleton["defense"] == 77
        assert updated_skeleton["evasion"] == 66
        assert updated_skeleton["accuracy_close"] == 55

        print("✅ Success! Selective rank save verified correctly. Other ranks were NOT modified.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise e
    finally:
        # Restore backup and kill server
        if server_process:
            print("Terminating server process...")
            server_process.terminate()
            server_process.wait()

        if os.path.exists(BACKUP_YML):
            print("Restoring backup of enemies.yml...")
            shutil.move(BACKUP_YML, ENEMIES_YML)
            print("Backup restored.")

if __name__ == "__main__":
    test_selective_save()
