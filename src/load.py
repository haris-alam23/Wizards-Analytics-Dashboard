from __future__ import annotations
import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

@dataclass(frozen = True)
class DBConfig: 
    host: str
    port: int
    db: str
    user: str
    password: str
    schema: str = "wizards"
    
    
    @staticmethod
    def from_env() -> "DBConfig":
        required = ["PGHOST","PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]
        missing = [r for r in required if not os.getenv(r)]
        if missing:
            raise RuntimeError(
                "Missing environment variables: " + ",".join(missing)
            )
            
        return DBConfig(
            host=os.environ["PGHOST"],
            port=int(os.environ["PGPORT"]),
            db=os.environ["PGDATABASE"],
            user=os.environ["PGUSER"],
            password=os.environ["PGPASSWORD"],
            schema=os.getenv("PGSCHEMA", "wizards"),
)
    

def start_engine(cfg: DBConfig) -> Engine:
    url = f"postgresql+psycopg2://{cfg.user}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.db}"
    return create_engine(url, future = True)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    
    df = pd.read_csv(path)
    
    return df


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    
    df = df.copy()
    df.columns = [column.strip().upper() for column in df.columns]
    
    return df


def validate_games(df: pd.DataFrame) -> None:
    
    required = {"GAME_ID", "PLAYER_ID", "GAME_DATE","PTS"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}.")
    
    duplicate = df.duplicated(subset = ["GAME_ID", "PLAYER_ID"]).sum()
    if duplicate > 0:
        raise ValueError(f"Found {duplicate} duplicates, (GAME_ID, PLAYER_ID) rows." )
    
    if (df["PTS"] < 0).any():
        raise ValueError("Found negative points.")
    
    try:
        pd.to_datetime(df["GAME_DATE"])
    except Exception as e:
        raise ValueError(f"GAME_DATE not parseable: {e}") from e
    

def ensure_schema(engine: Engine, schema: str) -> None:
    
    with engine.begin() as conn: 
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))
        
        
def write(engine: Engine, df: pd.DataFrame, schema: str, staging_table: str) -> None:
    
    df.to_sql(
        staging_table,
        engine,
        schema = schema,
        if_exists= "replace",
        index = False,
        method = "multi",
        chunksize = 10_000,
    )
    

def upsert_games(engine: Engine, schema: str, staging: str, target: str) -> None: 
        with engine.begin() as conn:
            conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {schema}.{target} (
                LIKE {schema}.{staging} INCLUDING DEFAULTS
            );
        """))
            
            conn.execute(text(f"""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = '{target}_game_player_ux'
                ) THEN
                    ALTER TABLE {schema}.{target}
                    ADD CONSTRAINT {target}_game_player_ux UNIQUE ("GAME_ID", "PLAYER_ID");
                END IF;
            END$$;            
    """))
            
            conn.execute(text(f"""
            INSERT INTO {schema}.{target}
            SELECT * FROM {schema}.{staging}
            ON CONFLICT ("GAME_ID", "PLAYER_ID")
            DO UPDATE SET
                "SEASON_ID" = EXCLUDED."SEASON_ID",
                "GAME_DATE" = EXCLUDED."GAME_DATE",
                "MATCHUP" = EXCLUDED."MATCHUP",
                "WL" = EXCLUDED."WL",
                "MIN" = EXCLUDED."MIN",
                "FGM" = EXCLUDED."FGM",
                "FGA" = EXCLUDED."FGA",
                "FG_PCT" = EXCLUDED."FG_PCT",
                "FG3M" = EXCLUDED."FG3M",
                "FG3A" = EXCLUDED."FG3A",
                "FG3_PCT" = EXCLUDED."FG3_PCT",
                "FTM" = EXCLUDED."FTM",
                "FTA" = EXCLUDED."FTA",
                "FT_PCT" = EXCLUDED."FT_PCT",
                "OREB" = EXCLUDED."OREB",
                "DREB" = EXCLUDED."DREB",
                "REB" = EXCLUDED."REB",
                "AST" = EXCLUDED."AST",
                "STL" = EXCLUDED."STL",
                "BLK" = EXCLUDED."BLK",
                "TOV" = EXCLUDED."TOV",
                "PF" = EXCLUDED."PF",
                "PTS" = EXCLUDED."PTS",
                "PLUS_MINUS" = EXCLUDED."PLUS_MINUS",
                "VIDEO_AVAILABLE" = EXCLUDED."VIDEO_AVAILABLE",
                "PLAYER_NAME" = EXCLUDED."PLAYER_NAME";
        """))
            
            
def load_pipeline(csv_path: Path, table_name: str) -> None:
    print(f"Loading: {csv_path}")
    
    df = read_csv(csv_path)
    df = standardize_columns(df)
    if "GAME_DATE" in df.columns:
        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], errors="raise").dt.date
    
    if table_name == "player_games":
        validate_games(df)
    
    cfg = DBConfig.from_env()
    engine = start_engine(cfg)
    
    ensure_schema(engine, cfg.schema)
    
    staging_table = f"{table_name}__staging"
    write(engine, df, cfg.schema, staging_table)
    
    if table_name == "player_games":
        upsert_games(engine, cfg.schema, staging_table, table_name)
   
        
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True, help="Path to processed CSV")
    p.add_argument("--table", required=True, help="Target table name (e.g., player_games)")
    return p.parse_args()
    
    
if __name__ == "__main__":
    try:
        args = parse_args()
        load_pipeline(Path(args.csv), args.table)
    except Exception as e:
        print(f"[load] ❌ error: {e}", file=sys.stderr)
        sys.exit(1)
        
    
    
