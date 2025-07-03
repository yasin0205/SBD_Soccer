import os
from SoccerNet.Downloader import SoccerNetDownloader
from SoccerNet.utils import getListGames

# --------------------------- CONFIGURATION --------------------------- #
CONFIG = {
    "league_keyword": "spain_laliga",                         # Filter by this keyword
    "video_quality_files": ["1_720p.mkv", "2_720p.mkv"],      # Files to download
    "password": "s0cc3rn3t",                                           # Set your SoccerNet password here
    "output_dir": os.path.join(os.getcwd(), "LaLiga_Videos") # Where to save the videos
}

# --------------------------- DOWNLOAD FUNCTION --------------------------- #
def download_league_videos(config):
    """
    Download video files for all games matching a league keyword.
    """
    downloader = SoccerNetDownloader(LocalDirectory=config["output_dir"])
    downloader.password = config["password"]

    # Get all games, across all splits (internally)
    all_games = getListGames(split="all")  # get all matches at once
    league_games = [g for g in all_games if config["league_keyword"] in g]

    print(f"Found {len(league_games)} matches for league: {config['league_keyword']}")

    # Download all matching games
    for idx, game in enumerate(league_games, 1):
        try:
            print(f"\n[{idx}/{len(league_games)}] Downloading: {game}")
            downloader.downloadGame(game=game, files=config["video_quality_files"])
        except Exception as e:
            print(f"⚠️ Failed to download {game}: {e}")

# --------------------------- MAIN ENTRY POINT --------------------------- #
if __name__ == "__main__":
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    download_league_videos(CONFIG)
