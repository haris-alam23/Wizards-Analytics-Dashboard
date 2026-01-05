

PLAYERS_SQL = """ 
    SElECT DISTINCT "PLAYER_ID", "PLAYER_NAME"
    FROM wizards.player_games
        ORDER BY "PLAYER_NAME";
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
    ORDER BY "GAME_DATE"; 

    """