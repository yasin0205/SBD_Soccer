import os
from goal_clip_extractor import GoalClipExtractor
from frame_extractor import FrameExtractor


def get_project_root():
    """
    Utility function to locate the root directory of the project.
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def build_config():
    """
    Define the configuration for goal clip extraction and frame extraction.
    
    - `seconds_before_goal`: How many seconds before the goal to start the clip.
    - `seconds_after_goal`: Default duration after goal unless overridden by label calue: visible and kick-off.
    - `fps`: Frames per second for frame extraction.
    - Directories for full matches, goal clips, and frames.
    """
    root = get_project_root()
    return {
        "video_extensions": (".mp4", ".avi", ".mov", ".mkv"),
        "annotation_extensions": (".json",),
        "seconds_before_goal": 20,
        "seconds_after_goal": 60,
        "fps": 25,
        "source_dir": os.path.join(root, "dataset", "full_length_soccer_match_and_annotation"),
        "target_dir": os.path.join(root, "dataset", "goal_clips"),
        "frames_dir": os.path.join(root, "dataset", "frames")
    }


def main():
    """
    Main execution point.

    Project Goal:
    -------------
    Automatically process full-length soccer matches and annotations to extract 
    short video clips centered around goals. For each goal:

    1. Start the clip `X` seconds before the goal (default: 20s).
    2. End the clip `Y` seconds after the goal (default: 60s), unless a kickoff 
       occurs after the goal and is marked as visible, in which case the clip ends 
       at the kickoff timestamp.
    3. Extract frames from each goal clip and store them under a structured folder
       by match and goal name.
    """
    config = build_config()

    frame_extractor = FrameExtractor(config)
    goal_extractor = GoalClipExtractor(config)
    goal_extractor.run(frame_extractor)


if __name__ == "__main__":
    main()
