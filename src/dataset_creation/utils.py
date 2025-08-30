# utils.py

import os


class FileManager:
    """
    Utility class for handling basic file system operations.
    """

    @staticmethod
    def find_files(folder_path, extensions):
        """
        Return a list of files in the folder that match the given extensions.

        Args:
            folder_path (str): Path to the directory to search.
            extensions (tuple): Tuple of allowed file extensions (e.g., ('.mp4', '.json')).

        Returns:
            List[str]: Filenames that match the given extensions.
        """
        return [f for f in os.listdir(folder_path) if f.lower().endswith(extensions)]

    @staticmethod
    def ensure_dir_exists(path):
        """
        Ensure that a directory exists. If it does not, create it.

        Args:
            path (str): Directory path to check or create.
        """
        os.makedirs(path, exist_ok=True)
