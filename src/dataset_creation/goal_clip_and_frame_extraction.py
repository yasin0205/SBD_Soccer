import os
import json
import cv2

class FileManager:
    """Utility class to handle file finding and path creation."""

    @staticmethod
    def find_files(folder_path, extensions):
        """Return list of files in folder_path matching given extensions."""
        return [f for f in os.listdir(folder_path)
                if f.lower().endswith(extensions)]

    @staticmethod
    def ensure_dir_exists(path):
        """Create directory if it does not exist."""
        os.makedirs(path, exist_ok=True)


class GoalClipExtractor:
    """
    Extract goal clips from soccer match videos based on annotations.
    """

    def __init__(self, config):
        self.video_ext = config["video_extensions"]
        self.annotation_ext = config["annotation_extensions"]
        self.sec_before = config["seconds_before_goal"]
        self.sec_after = config["seconds_after_goal"]
        self.source_dir = config["source_dir"]
        self.target_dir = config["target_dir"]

    def parse_game_time(self, game_time_str):
        """
        Convert "1 - 00:30" to (video_index=1, seconds=30)
        """
        video_idx_str, time_str = game_time_str.split(" - ")
        video_idx = int(video_idx_str.strip())
        mins, secs = map(int, time_str.strip().split(":"))
        return video_idx, mins * 60 + secs

    def get_video_dict(self, folder_path):
        """
        Find videos starting with '1_' or '2_' and map them by video index.
        """
        videos = FileManager.find_files(folder_path, self.video_ext)
        video_dict = {}
        for v in videos:
            if v.startswith("1_"):
                video_dict[1] = v
            elif v.startswith("2_"):
                video_dict[2] = v
        return video_dict

    def get_annotation_file(self, folder_path):
        """
        Find first annotation JSON file in folder.
        """
        ann_files = FileManager.find_files(folder_path, self.annotation_ext)
        return ann_files[0] if ann_files else None

    def cut_clip(self, video_path, start_sec, end_sec, output_path):
        """
        Extract and save clip from video between start_sec and end_sec.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Cannot open video: {video_path}")
            return False

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)

        start_frame = int(fps * start_sec)
        end_frame = min(int(fps * end_sec), int(total_frames) - 1)

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        for frame_no in range(start_frame, end_frame + 1):
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)

        cap.release()
        out.release()
        return True

    def process_annotation(self, annotation_path):
        """
        Load annotation JSON and return list of goal events.
        """
        with open(annotation_path, 'r') as f:
            data = json.load(f)
        return [ann for ann in data.get("annotations", []) if ann.get("label", "").lower() == "goal"]

    def process_folder(self, folder_path, target_folder_path, frame_extractor):
        """
        Process a single match folder:
        - find videos and annotation
        - cut goal clips
        - extract frames from each goal clip
        """
        print(f"Processing folder: {folder_path}")
        video_dict = self.get_video_dict(folder_path)
        if not video_dict:
            print("No suitable videos found.")
            return

        annotation_file = self.get_annotation_file(folder_path)
        if not annotation_file:
            print("No annotation file found.")
            return

        annotation_path = os.path.join(folder_path, annotation_file)
        goals = self.process_annotation(annotation_path)

        FileManager.ensure_dir_exists(target_folder_path)

        for idx, goal in enumerate(goals, start=1):
            try:
                video_idx, goal_sec = self.parse_game_time(goal["gameTime"])
            except Exception as e:
                print(f"Failed to parse gameTime '{goal.get('gameTime', '')}': {e}")
                continue

            if video_idx not in video_dict:
                print(f"Video {video_idx} not found.")
                continue

            video_file = video_dict[video_idx]
            video_path = os.path.join(folder_path, video_file)

            start_sec = max(0, goal_sec - self.sec_before)
            end_sec = goal_sec + self.sec_after

            team = goal.get("team", "unknown")
            safe_game_time = goal["gameTime"].replace(" ", "_").replace(":", "-")
            clip_name = f"{safe_game_time}_{team}_goal{idx}.mp4"
            clip_path = os.path.join(target_folder_path, clip_name)

            print(f"Cutting clip {clip_name} from {start_sec}s to {end_sec}s")
            success = self.cut_clip(video_path, start_sec, end_sec, clip_path)

            if success:
                # Extract frames from the clip
                match_name = os.path.basename(folder_path)
                goal_folder = os.path.splitext(clip_name)[0]
                frames_folder = os.path.join(frame_extractor.frames_dir, match_name, goal_folder)
                frame_extractor.extract_frames(clip_path, frames_folder)

    def run(self, frame_extractor):
        """
        Walk through all match folders and process them.
        """
        FileManager.ensure_dir_exists(self.target_dir)
        FileManager.ensure_dir_exists(frame_extractor.frames_dir)

        for folder_name in os.listdir(self.source_dir):
            folder_path = os.path.join(self.source_dir, folder_name)
            if os.path.isdir(folder_path):
                target_folder_path = os.path.join(self.target_dir, folder_name)
                self.process_folder(folder_path, target_folder_path, frame_extractor)


class FrameExtractor:
    """
    Extract frames from goal clips at desired FPS, saving in structured folders.
    """

    def __init__(self, config):
        self.target_fps = config.get("fps", 25)
        self.frames_dir = config.get("frames_dir")

    def extract_frames(self, video_path, save_folder):
        FileManager.ensure_dir_exists(save_folder)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Cannot open clip for frame extraction: {video_path}")
            return

        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if video_fps <= 0:
            video_fps = self.target_fps

        # Calculate frame interval to downsample or keep fps
        frame_interval = max(1, int(round(video_fps / self.target_fps)))

        frame_idx = 0
        saved_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                frame_name = f"frame_{saved_idx:04d}.jpg"
                cv2.imwrite(os.path.join(save_folder, frame_name), frame)
                saved_idx += 1

            frame_idx += 1

        cap.release()
        print(f"Extracted {saved_idx} frames to {save_folder}")


if __name__ == "__main__":
    config = {
        "video_extensions": ('.mp4', '.avi', '.mov', '.mkv'),
        "annotation_extensions": ('.json',),
        "seconds_before_goal": 20,
        "seconds_after_goal": 20,
        "fps": 25,
        "source_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dataset", "full_length_soccer_match_and_annotation")),
        "target_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dataset", "goal_clips")),
        "frames_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dataset", "frames")),
    }

    frame_extractor = FrameExtractor(config)
    goal_extractor = GoalClipExtractor(config)
    goal_extractor.run(frame_extractor)
