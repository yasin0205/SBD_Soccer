# frame_extractor.py
import os
import cv2
from utils import FileManager


class FrameExtractor:
    """
    Extracts frames from video clips at a defined frame-per-second (FPS) rate
    and saves them into structured directories.
    """

    def __init__(self, config):
        self.target_fps = config.get("fps", 25)
        self.frames_dir = config.get("frames_dir")

    def extract_frames(self, video_path, save_folder):
        """
        Extract frames from a video clip and save them to the specified folder
        at the desired target FPS.
        """
        FileManager.ensure_dir_exists(save_folder)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[ERROR] Cannot open video: {video_path}")
            return

        original_fps = cap.get(cv2.CAP_PROP_FPS)
        if original_fps <= 0:
            print("[WARNING] FPS not detected, defaulting to target FPS.")
            original_fps = self.target_fps

        interval = max(1, int(round(original_fps / self.target_fps)))
        frame_idx = 0
        saved_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % interval == 0:
                frame_filename = f"frame_{saved_idx:04d}.jpg"
                frame_path = os.path.join(save_folder, frame_filename)
                cv2.imwrite(frame_path, frame)
                saved_idx += 1

            frame_idx += 1

        cap.release()
        print(f"[INFO] Extracted {saved_idx} frames to: {save_folder}")
