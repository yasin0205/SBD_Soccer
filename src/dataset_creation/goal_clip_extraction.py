import os

def get_directory_structure(base_dir):
    directory_structure = []

    for folder_name, subfolders, filenames in os.walk(base_dir):
        directory_structure.append({
            "folder": folder_name,
            "subfolders": subfolders,
            "files": filenames
        })

    return directory_structure


# Example usage
if __name__ == "__main__":
    current_dir = os.path.dirname(__file__)
    video_and_annotation_dir = os.path.abspath(
        os.path.join(current_dir, "..", "..", "dataset", "full_length_soccer_match_and_annotation"))

    structure = get_directory_structure(video_and_annotation_dir)

    for entry in structure:
        print(f"The current folder is: {entry['folder']}")
        for subfolder in entry['subfolders']:
            print(f"  Subfolder of {entry['folder']}: {subfolder}")
        for file in entry['files']:
            print(f"  File inside {entry['folder']}: {file}")
