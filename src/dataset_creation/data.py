import json
import os

# Path to JSON
json_path = os.path.join(os.path.dirname(__file__), "Labels-v2.json")

# Load JSON
with open(json_path, 'r') as f:
    json_data = json.load(f)

# Print metadata
print(f"Match: {json_data.get('UrlLocal')}")
print(f"Home Team: {json_data.get('gameHomeTeam')}")
print(f"Away Team: {json_data.get('gameAwayTeam')}")
print(f"Score: {json_data.get('gameScore')}")
print(f"Date: {json_data.get('gameDate')}")

# Get annotations
annotations = json_data.get("annotations", [])

# Loop through annotations by index
for i in range(len(annotations) - 1):  # stop at second last item
    current = annotations[i]
    next_ann = annotations[i + 1]

    if current.get('label') == 'Goal':
        print(
            f"\n[GOAL] Time: {current.get('gameTime')}, Position: {current.get('position')}, "
            f"Team: {current.get('team')}, Visibility: {current.get('visibility')}"
        )

        if (
            next_ann.get('label') == 'Kick-off'
            and next_ann.get('visibility') == 'not shown'
        ):
            print("  ⚠️ Kick-off is not shown. We are cutting the video at default second: 80")
