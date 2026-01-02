import json
from pathlib import Path
from datetime import datetime
from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster
from nba_api.stats.endpoints import playergamelog
from typing import Union
import time


Raw_Dir = Path("data/raw")
Raw_Dir.mkdir(parents = True, exist_ok = True)



def save_raw(obj: dict, name: str) -> Path:
    
    ts = datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
    path = Raw_Dir / f"{name}_{ts}.json"
    
    with open(path, "w") as f:
        json.dump(obj, f, indent = 2)

    return path


def load_json(path: Union[str, Path]) -> dict:
    path = Path(path)
    with open(path, "r") as f:
        return json.load(f)


def get_wizards() -> dict:
    
    all_teams = teams.get_teams()
    wizards = next(t for t in all_teams if t["full_name"] == "Washington Wizards" )
    return wizards


def fetch_wizards_roster(team_id: int, season: str) -> dict:
    
    time.sleep(1.0)
    endpoint = commonteamroster.CommonTeamRoster(team_id = team_id, season = season)
    data = endpoint.get_dict()
    return data


def resultset_to_dict(result_set: dict) -> list[dict]:
    
    headers = result_set["headers"]
    rows = result_set["rowSet"]
    return [dict(zip(headers, row)) for row in rows]    


def extract_roster_players(roster_data: dict) -> list[dict]:
    
    result_sets = roster_data["resultSets"]
    rosters = next(row for row in result_sets if row["name"] == "CommonTeamRoster")
    rosters_rows = resultset_to_dict(rosters)
    
    return [{"PLAYER_ID": r["PLAYER_ID"], "PLAYER": r["PLAYER"], "POSITION": r["POSITION"]} for r in rosters_rows]
    
    
def newest_raw_file(prefix: str) -> Path:
    
    matches = sorted(Raw_Dir.glob(f"{prefix}_*.json"))
    if not matches:
        raise FileNotFoundError(f"No raw files found matching prefix: {prefix}")
    return matches[-1]


def fetch_player_game_log(player_id: int, season: str) -> dict:
    
    time.sleep(1.0)
    endpoint = playergamelog.PlayerGameLog(player_id = player_id, season = season)
    return endpoint.get_dict()

    
def fetch_all_players_game_log(players:list[dict], season: str):
    
    for i, player in enumerate(players, start=1):
        player_id = player["PLAYER_ID"]
        player_name = player["PLAYER"]
        
        print(f"[{i}/{len(players)}] Fetching game log for {player_name}")
        
        try:
            gamelog = fetch_player_game_log(player_id = player_id, season = season)
            save_raw(
                gamelog, 
                f"gamelog_{season.replace('-', '_')}_{player_id}_{player_name.replace(' ', '_')}"
            )
        except Exception as e:
            print(f"Failed for player:{player_name} ({player_id}): {e}")
            
        time.sleep(1.5)
            
            
            
        
            
        
        
        
if __name__ == "__main__":
    season = "2025-26"

    # Load most recent player ID file
    player_ids_file = newest_raw_file("wizards_player_ids_2025_26")
    players_data = load_json(player_ids_file)
    players = players_data["players"]

    print(f"Loaded {len(players)} players from {player_ids_file}")

    fetch_all_players_game_log(players, season)
    