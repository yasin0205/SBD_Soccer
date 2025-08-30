# goal_clip_extractor.py
import os
import json
import cv2
from utils import FileManager


class GoalClipExtractor:
    """
    Extracts goal-specific clips from full-length soccer match videos based on event annotations.
    Each goal clip includes seconds before the goal and extends either to a fixed window after,
    or until the next visible kick-off (if annotated).
    """

    def __init__(self, config):
        self.video_ext = config["video_extensions"]
        self.annotation_ext = config["annotation_extensions"]
        self.sec_before = config["seconds_before_goal"]
        self.sec_after = config["seconds_after_goal"]
        self.source_dir = config["source_dir"]
        self.target_dir = config["target_dir"]

    def parse_game_time(self, game_time_str):
        """Convert game time string '1 - 00:30' to (video_index=1, seconds=30)."""
        video_idx_str, time_str = game_time_str.split(" - ")
        video_idx = int(video_idx_str.strip())
        mins, secs = map(int, time_str.strip().split(":"))
        return video_idx, mins * 60 + secs

    def get_video_dict(self, folder_path):
        """Return dict mapping video indices (1/2) to filenames."""
        videos = FileManager.find_files(folder_path, self.video_ext)
        return {
            1: next((v for v in videos if v.startswith("1_")), None),
            2: next((v for v in videos if v.startswith("2_")), None)
        }

    def get_annotation_file(self, folder_path):
        """Return the first annotation file in the folder, if any."""
        files = FileManager.find_files(folder_path, self.annotation_ext)
        return files[0] if files else None

    def load_annotations(self, annotation_path):
        """Load JSON annotation and return list of all events."""
        with open(annotation_path, 'r') as f:
            data = json.load(f)
        return data.get("annotations", [])

    def extract_goal_annotations(self, annotations):
        """Return indices of all annotations labeled 'goal'."""
        return [i for i, ann in enumerate(annotations) if ann.get("label", "").lower() == "goal"]

    def determine_clip_times(self, annotations, goal_idx):
        """
        Determine clip start/end time based on goal annotation and next visible kick-off.
        """
        goal = annotations[goal_idx]
        video_idx, goal_sec = self.parse_game_time(goal["gameTime"])
        start_sec = max(0, goal_sec - self.sec_before)
        end_sec = goal_sec + self.sec_after

        if goal_idx + 1 < len(annotations):
            next_ann = annotations[goal_idx + 1]
            if next_ann.get("label", "").lower() == "kick-off" and \
               next_ann.get("visibility", "").lower() == "visible":
                try:
                    _, end_sec = self.parse_game_time(next_ann["gameTime"])
                except Exception:
                    pass

        return video_idx, start_sec, end_sec

    def generate_clip_name(self, goal, clip_num):
        """Create filename for the goal clip."""
        team = goal.get("team", "unknown")
        safe_time = goal["gameTime"].replace(" ", "_").replace(":", "-")
        return f"{safe_time}_{team}_goal{clip_num}.mp4"

    def cut_clip(self, video_path, start_sec, end_sec, output_path):
        """
        Cut a clip from video between start_sec and end_sec and save to output_path.
        Returns True if successful.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[ERROR] Cannot open video: {video_path}")
            return False

        fps = cap.get(cv2.CAP_PROP_FPS)
        start_frame = int(fps * start_sec)
        end_frame = int(fps * end_sec)

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        for _ in range(start_frame, end_frame + 1):
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)

        cap.release()
        out.release()
        return True

    def handle_single_goal(self, annotations, goal_idx, video_dict, folder_path, target_folder, clip_num, frame_extractor):
        """Process one goal annotation: cut clip, save, and extract frames."""
        try:
            video_idx, start_sec, end_sec = self.determine_clip_times(annotations, goal_idx)
        except Exception as e:
            print(f"[WARNING] Skipping goal (bad time): {e}")
            return

        if video_idx not in video_dict or not video_dict[video_idx]:
            print(f"[WARNING] Video index {video_idx} not found.")
            return

        goal = annotations[goal_idx]
        video_path = os.path.join(folder_path, video_dict[video_idx])
        clip_name = self.generate_clip_name(goal, clip_num)
        clip_path = os.path.join(target_folder, clip_name)

        print(f"→ Cutting: {clip_name} ({start_sec}s to {end_sec}s)")
        success = self.cut_clip(video_path, start_sec, end_sec, clip_path)

        if success:
            match_name = os.path.basename(folder_path)
            goal_folder = os.path.splitext(clip_name)[0]
            frame_output_path = os.path.join(frame_extractor.frames_dir, match_name, goal_folder)
            frame_extractor.extract_frames(clip_path, frame_output_path)

    def process_folder(self, folder_path, target_folder, frame_extractor):
        """Extract goal clips from a single match folder."""
        print(f"[INFO] Processing match: {folder_path}")

        video_dict = self.get_video_dict(folder_path)
        if not any(video_dict.values()):
            print("→ No valid video files found.")
            return

        ann_file = self.get_annotation_file(folder_path)
        if not ann_file:
            print("→ No annotation file found.")
            return

        annotations = self.load_annotations(os.path.join(folder_path, ann_file))
        goal_indices = self.extract_goal_annotations(annotations)

        FileManager.ensure_dir_exists(target_folder)

        for i, goal_idx in enumerate(goal_indices, start=1):
            self.handle_single_goal(
                annotations, goal_idx, video_dict,
                folder_path, target_folder, i,
                frame_extractor
            )

    def run(self, frame_extractor):
        """
        Traverse all match folders under source_dir,
        extract goal clips and corresponding frames.
        """
        FileManager.ensure_dir_exists(self.target_dir)
        FileManager.ensure_dir_exists(frame_extractor.frames_dir)

        for folder_name in os.listdir(self.source_dir):
            match_path = os.path.join(self.source_dir, folder_name)
            if os.path.isdir(match_path):
                target_path = os.path.join(self.target_dir, folder_name)
                self.process_folder(match_path, target_path, frame_extractor)
