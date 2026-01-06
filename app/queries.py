

PLAYERS_SQL = """ 
    SELECT DISTINCT "PLAYER_ID", "PLAYER_NAME"
    FROM wizards.player_games
        ORDER BY "PLAYER_NAME";
"""

SEASONS_SQL = """
    SELECT DISTINCT "SEASON_ID"
    FROM wizards.player_games
    ORDER BY "SEASON_ID";
"""

PLAYER_GAMES_SQL = """
    SELECT
        "GAME_DATE",
        "MATCHUP",
        "WL",
        "MIN",
        "PTS",
        "AST",
        "REB",
        "FGM",
        "FGA",
        "FG3M",
        "FG3A",
        "PLUS_MINUS",
        "SEASON_ID"
    FROM wizards.player_games
    WHERE "PLAYER_ID" = %(player_id)s
        AND (%(season_id)s IS NULL OR "SEASON_ID" = %(season_id)s)
    ORDER BY "GAME_DATE"; 

    """