import os
import json
import cv2

# --- CONFIGURATION ---
CONFIG = {
    "video_extensions": ('.mp4', '.avi', '.mov', '.mkv'),
    "annotation_extensions": ('.json',),
    "seconds_before_goal": 20,
    "seconds_after_goal": 20,
    "source_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dataset", "full_length_soccer_match_and_annotation")),
    "target_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dataset", "goal_clips"))
}
# ----------------------

def parse_game_time(game_time_str):
    """
    Parse gameTime string like "1 - 00:00" into (video_index, seconds)
    """
    video_idx_str, time_str = game_time_str.split(" - ")
    video_idx = int(video_idx_str.strip())
    mins, secs = map(int, time_str.strip().split(":"))
    total_seconds = mins * 60 + secs
    return video_idx, total_seconds

def cut_goal_clip(video_path, start_sec, end_sec, output_path):
    """
    Cut video clip from start_sec to end_sec (seconds) and save it.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Cannot open video: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)

    start_frame = int(fps * start_sec)
    end_frame = int(fps * end_sec)
    end_frame = min(end_frame, int(total_frames) - 1)

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    current_frame = start_frame
    while current_frame <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        current_frame += 1

    cap.release()
    out.release()

def process_subfolder(subfolder_path, target_subfolder_path):
    videos = [f for f in os.listdir(subfolder_path)
              if f.lower().endswith(CONFIG["video_extensions"])]

    if not videos:
        print(f"No video files found in {subfolder_path}, skipping.")
        return

    video_dict = {}
    for v in videos:
        if v.startswith("1_"):
            video_dict[1] = v
        elif v.startswith("2_"):
            video_dict[2] = v

    if not video_dict:
        print(f"No properly named videos starting with '1_' or '2_' found in {subfolder_path}, skipping.")
        return

    annotation_files = [f for f in os.listdir(subfolder_path)
                        if f.lower().endswith(CONFIG["annotation_extensions"])]
    if not annotation_files:
        print(f"No annotation file found in {subfolder_path}, skipping.")
        return
    annotation_path = os.path.join(subfolder_path, annotation_files[0])

    with open(annotation_path, 'r') as f:
        annotation_data = json.load(f)

    annotations = annotation_data.get("annotations", [])

    goal_count = 0
    for ann in annotations:
        if ann.get("label", "").lower() == "goal":
            goal_count += 1

            game_time = ann.get("gameTime", "")
            try:
                video_idx, goal_sec = parse_game_time(game_time)
            except Exception as e:
                print(f"Failed to parse gameTime '{game_time}' in {subfolder_path}: {e}")
                continue

            if video_idx not in video_dict:
                print(f"Video index {video_idx} not found among videos in {subfolder_path}")
                continue

            video_file = video_dict[video_idx]
            video_path = os.path.join(subfolder_path, video_file)

            start_sec = max(0, goal_sec - CONFIG["seconds_before_goal"])
            end_sec = goal_sec + CONFIG["seconds_after_goal"]

            team = ann.get("team", "unknown")
            safe_game_time = game_time.replace(" ", "_").replace(":", "-")
            output_filename = f"{safe_game_time}_{team}_goal{goal_count}.mp4"
            output_path = os.path.join(target_subfolder_path, output_filename)

            print(f"Cutting goal clip: {output_path} from {start_sec}s to {end_sec}s")
            cut_goal_clip(video_path, start_sec, end_sec, output_path)

def main():
    os.makedirs(CONFIG["target_dir"], exist_ok=True)

    for subfolder_name in os.listdir(CONFIG["source_dir"]):
        subfolder_path = os.path.join(CONFIG["source_dir"], subfolder_name)
        if os.path.isdir(subfolder_path):
            target_subfolder_path = os.path.join(CONFIG["target_dir"], subfolder_name)
            os.makedirs(target_subfolder_path, exist_ok=True)
            process_subfolder(subfolder_path, target_subfolder_path)

if __name__ == "__main__":
    main()
