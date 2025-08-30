"""
SoccerNet Game Downloader (Flat Structure)
------------------------------------------
Downloads SoccerNet matches into a flat folder.
Supports interactive filtering and multiple selections.
"""

import os
import pandas as pd
import shutil
from SoccerNet.utils import getListGames
from SoccerNet.Downloader import SoccerNetDownloader
from concurrent.futures import ThreadPoolExecutor

# =====================================================================
# CONFIGURATION
# =====================================================================
try:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
except NameError:
    BASE_DIR = os.path.abspath(os.path.join(os.getcwd(), "..", ".."))

OUTPUT_DIR = os.path.join(BASE_DIR, "dataset", "full_length_soccer_match_and_annotation")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CONFIG = {
    "output_dir": OUTPUT_DIR,
    "password": "",
    "max_workers": 4,
    "default_resolution": "720",
    "label_file": "Labels-v2.json"
}

# =====================================================================
# HELPER FUNCTIONS
# =====================================================================
def fetch_games():
    all_games = getListGames(split=["train", "valid", "test", "challenge"])
    df = pd.DataFrame(all_games, columns=["Games"])

    pattern = (
        r'^(?P<league>[^\\]+)\\(?P<season>[^\\]+)\\'
        r'(?P<date>\d{4}-\d{2}-\d{2})\s*-\s*'
        r'(?P<time>\d{2}-\d{2})\s+'
        r'(?P<home_team>.+?)\s+(?P<home_score>\d+)\s*-\s*'
        r'(?P<away_score>\d+)\s+(?P<away_team>.+)$'
    )

    parsed_df = df["Games"].str.extract(pattern)
    parsed_df = parsed_df[["league", "season", "date", "time", "home_team", "home_score", "away_score", "away_team"]]
    return parsed_df, all_games


def select_resolution():
    choice = input(f"Select resolution (224 or 720, default {CONFIG['default_resolution']}): ").strip()
    if choice == "224":
        return ["1_224p.mkv", "2_224p.mkv", CONFIG["label_file"]]
    return ["1_720p.mkv", "2_720p.mkv", CONFIG["label_file"]]


def interactive_search(parsed_df):
    filtered = parsed_df.copy()

    def multi_select(column_name, display_name):
        unique_values = filtered[column_name].unique()
        print(f"\nAvailable {display_name}: {list(unique_values)}")
        user_input = input(f"Select {display_name} (comma-separated, Enter to skip): ").strip()
        if user_input:
            choices = [x.strip() for x in user_input.split(",")]
            return filtered[filtered[column_name].isin(choices)]
        return filtered

    filtered = multi_select('league', 'leagues')
    filtered = multi_select('season', 'seasons')
    filtered = multi_select('home_team', 'home teams')
    filtered = multi_select('away_team', 'away teams')
    filtered = multi_select('date', 'dates')

    if filtered.empty:
        print("\n❌ No matching games found.")
        return None

    print("\n✅ Matching games:")
    print(filtered)

    filtered_csv = os.path.join(CONFIG["output_dir"], "filtered_games.csv")
    filtered.to_csv(filtered_csv, index=False)
    print(f"\n📂 Filtered results saved to: {filtered_csv}")

    return filtered


def download_game_row(row, all_games, downloader, files):
    match_str = (
        f"{row['league']}/{row['season']}/{row['date']} - {row['time']} "
        f"{row['home_team']} {row['home_score']} - {row['away_score']} {row['away_team']}"
    )
    matched_games = [g for g in all_games if g.replace("\\", "/").endswith(match_str)]

    if not matched_games:
        print(f"⚠️ WARNING: Game not found → {match_str}")
        return

    print(f"⬇️ Downloading: {matched_games[0]}")

    # Download to default nested structure
    downloader.downloadGame(matched_games[0], files=files)

    # Move to flat folder
    nested_dir = os.path.join(CONFIG["output_dir"], matched_games[0].replace("/", os.sep))
    flat_name = f"{row['date']} - {row['time']} {row['home_team']} {row['home_score']} - {row['away_score']} {row['away_team']}"
    target_dir = os.path.join(CONFIG["output_dir"], flat_name)
    os.makedirs(target_dir, exist_ok=True)

    for f in files:
        src = os.path.join(nested_dir, f)
        if os.path.exists(src):
            shutil.move(src, os.path.join(target_dir, f))

    # Clean up empty nested folders
    try:
        shutil.rmtree(os.path.join(CONFIG["output_dir"], row['league']))
    except Exception:
        pass

    print(f"✅ Saved match in flat folder: {target_dir}")


def download_games(filtered_df, all_games, downloader, files, max_workers=4):
    count = len(filtered_df)
    print(f"\nTotal games to download: {count}")
    confirm = input(f"Ready to download {count} games? (y/n): ").strip().lower()
    if confirm != "y":
        print("❌ Download cancelled.")
        return

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda row: download_game_row(row, all_games, downloader, files),
                     [row for _, row in filtered_df.iterrows()])

    print("\n✅ All selected matches downloaded successfully.")


def main():
    print("\n⚽ SoccerNet Interactive Game Downloader ⚽")

    parsed_df, all_games = fetch_games()

    downloader = SoccerNetDownloader(LocalDirectory=CONFIG["output_dir"])
    downloader.password = CONFIG["password"]

    files_to_download = select_resolution()

    filtered_games = interactive_search(parsed_df)
    if filtered_games is not None:
        download_games(filtered_games, all_games, downloader, files_to_download, CONFIG["max_workers"])


if __name__ == "__main__":
    main()
