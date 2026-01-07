import json
import pandas as pd
import re
from pathlib import Path


Raw_Dir = Path("data/raw")
Processed_Dir = Path("data/processed")
Processed_Dir.mkdir(parents = True, exist_ok = True)

FileName_RE = re.compile(r"^gamelog_(?P<season>\d{4}_\d{2})_(?P<player_id>\d+)_(?P<player_name>.+)_(?P<ts>\d{4}\.\d{2}\.\d{2}_\d{2}\.\d{2}\.\d{2})$")

def parse_game_log_filename(path: Path) -> tuple[str, int, str]: 
    
    m = FileName_RE.match(path.stem)
    if not m:
        raise ValueError(f"Filename format unexpected: {path.name}")
    
    season = m.group("season")
    player_id = int(m.group("player_id"))
    player_name = m.group("player_name").replace("_", " ")
    return season, player_id, player_name


def resultset_to_df(result_set: dict) -> pd.DataFrame:
    
    headers = result_set["headers"]
    rows = result_set["rowSet"]
    return pd.DataFrame(rows, columns = headers)


def parse_player_game_log(path: Path) -> pd.DataFrame:
    season, player_id, player_name = parse_game_log_filename(path)
    with open(path, "r") as f:
        data = json.load(f)
        
    result_set = data["resultSets"]
    gamelog_row = next(row for row in result_set if row["name"] == "PlayerGameLog")
    
    df = resultset_to_df(gamelog_row)
    df["PLAYER_ID"] = player_id
    df["PLAYER_NAME"] = player_name
    return df


def parse_all_players_game_log(season: str) -> pd.DataFrame:
    files = sorted(Raw_Dir.glob(f"gamelog_{season.replace('-', '_')}_*.json"))
    
    if not files:
        raise FileNotFoundError("No game log files found")
    
    dfs = []
    for file in files: 
        df = parse_player_game_log(file)
        dfs.append(df)
        
    combined = pd.concat(dfs, ignore_index = True)    
    return combined

def save_processed_game_logs(df: pd.DataFrame, season: str) -> Path:
    
    out_path = Processed_Dir / f"player_game_logs_{season.replace('-', '_')}.csv"
    df.to_csv(out_path, index=False)
    return out_path


if __name__ == "__main__":
    seasons_found = sorted({
        parse_game_log_filename(p)[0].replace("_", "-") 
        for p in Raw_Dir.glob("gamelog_*.json")
    })
    
    if not seasons_found:
        raise FileNotFoundError(f"No gamelog_*.json files found in {Raw_Dir}")

    all_dfs = []
    for season in seasons_found:
        print(f"\n=== Transforming season {season} ===")
        df_season = parse_all_players_game_log(season)
        all_dfs.append(df_season)

    df = pd.concat(all_dfs, ignore_index=True)
    if "Player_ID" in df.columns:
        df = df.drop(columns=["Player_ID"])
        
    game_id_col = "GAME_ID" if "GAME_ID" in df.columns else "Game_ID"
    df = df.drop_duplicates(subset=["PLAYER_ID", game_id_col])

    print("Combined rows:", len(df))
    print("Columns:", list(df.columns))
    print(df.head(5))

    out = Processed_Dir / "player_game_logs_all_seasons.csv"
    df.to_csv(out, index=False)
    print("Saved processed game logs to:", out)


    
    

