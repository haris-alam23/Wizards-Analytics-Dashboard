import streamlit as st
import pandas as pd
import plotly.express as px 
from db import get_engine
from queries import PLAYERS_SQL, PLAYER_GAMES_SQL
import plotly.graph_objects as go




st.set_page_config(
    page_title= "Washington Wizards Analytics Dashboard",
    layout= "wide"
)


st.markdown(
"""<div style="
background: radial-gradient(circle at center,
rgba(0,43,92,1) 0%,
rgba(227,24,55,1) 45%,
rgba(0,43,92,1) 100%);
padding: 6rem 4rem;
border-radius: 18px;
margin-bottom: 1.75rem;">
<div style="
color: white;
font-size: 2.7rem;
font-weight: 700;
line-height: 1.15;
margin-bottom: 0.4rem;">
Washington Wizards Analytics Dashboard
</div>
<div style="
color: rgba(255,255,255,0.85);
font-size: 1rem;">
Player performance overview and scoring analytics
</div>
</div>""",
unsafe_allow_html=True
)



@st.cache_data(ttl=300)
def load_players() -> pd.DataFrame:
    
    engine = get_engine()
    return pd.read_sql(PLAYERS_SQL, engine)

@st.cache_data(ttl=300)
def load_player_games(player_id: int) -> pd.DataFrame:
    
    engine = get_engine()
    return pd.read_sql(PLAYER_GAMES_SQL, engine, params={"player_id": player_id})





st.sidebar.header("Filters")

players_df = load_players()

name = st.sidebar.selectbox("Player", players_df["PLAYER_NAME"].tolist())
name_id_match = players_df.loc[players_df["PLAYER_NAME"] == name, "PLAYER_ID"]
if name_id_match.empty:
    st.error("Player not found")
    st.stop()
player_id = int(name_id_match.iloc[0])


df = load_player_games(player_id)
seasons = sorted(df["SEASON_ID"].dropna().unique().tolist())
season = st.sidebar.selectbox("Season", seasons) if seasons else None
if season is not None:
    df = df[df["SEASON_ID"] == season]

df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
min_date = df["GAME_DATE"].min()
max_date = df["GAME_DATE"].max()
date_range = st.sidebar.date_input("Date Range",value= (min_date.date(), max_date.date()), min_value= min_date.date(),max_value= max_date.date())
start_date, end_date = date_range
df = df[(df["GAME_DATE"].dt.date >= start_date) & (df["GAME_DATE"].dt.date <= end_date)]

st.sidebar.caption(f"{len(df)} games selected")
if df.empty:
    st.warning("No games found for these filters.")
    st.stop()
    
    
# Field Goal %
df["FG_PCT"] = df.apply(lambda r: (r["FGM"] / r["FGA"]) if r["FGA"] else None, axis = 1)

points_avg = df["PTS"].mean()
assist_avg = df["AST"].mean()
rebound_avg = df["REB"].mean()
fg_pct = df["FG_PCT"].mean()
pm_avg = df["PLUS_MINUS"].mean()

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Points (avg)", f"{points_avg:.1f}")
col2.metric("Assists (avg)", f"{assist_avg:.1f}")
col3.metric("Rebounds (avg)", f"{rebound_avg:.1f}")
col4.metric("FG % (avg)",f"{(fg_pct*100):.1f}%" if fg_pct is not None else "-")
col5.metric("Plus/Minus (avg)", f"{pm_avg:.1f}")


performance_tab, log_tab = st.tabs(["📈 Performance", "📋 Game Log"])




with performance_tab:
    window = st.selectbox("Rolling window (games)", [3,5,10], index=0)
    df["PTS_ROLL"] = df["PTS"].rolling(window=window, min_periods= window).mean()

    
    st.subheader("Player Form")
    season_avg = df["PTS"].mean()
    season_std = df["PTS"].std()
    newest_roll = df["PTS_ROLL"].iloc[-1]
    if season_std and not pd.isna(newest_roll):
        streak_score = (newest_roll - season_avg) / season_std
    else:
        streak_score = 0

    if streak_score >= 1.0:
        status = "🔥 Hot"
        reason = "Recent scoring well above season average"
    elif streak_score <= -1.0:
        status = "❄️ Cold"
        reason = "Recent scoring well below season average"
    else:
        status = "Neutral"
        reason = "Recent scoring near season average"
        
    c1, c2, c3 = st.columns(3)

    c1.metric("Form Status", status)
    c2.metric("Streak Score (z)", f"{streak_score:.2f}")
    c3.metric("Recent Avg (PTS)", f"{newest_roll:.1f}")

    st.caption(reason)
    
    st.divider()
    
    st.subheader("Scoring Trends")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["GAME_DATE"],
            y=df["PTS"],
            mode="lines+markers",
            name="Points",
            opacity=0.35
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["GAME_DATE"],
            y=df["PTS_ROLL"],
            mode="lines",
            name=f"{window}-Game Rolling Avg",
            line=dict(width=3)
        )
    )
    fig.update_layout(
    
        xaxis_title="Game Date",
        yaxis_title="Points",
        hovermode="x unified",
        margin=dict(t=60, l=40, r=40, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)


    st.subheader("Scoring vs Minutes Played")


    scatter_df = df.dropna(subset=["MIN", "PTS"]).copy()



    fig_scatter = px.scatter(
        scatter_df,
        x="MIN",
        y= "PTS",
        labels= {
            "MIN": "Minutes Played",
            "PTS": "Points Scored",
            "WL": "Result"
        },
        opacity= 0.7,
        trendline= "ols"
    )
    fig_scatter.update_traces(
        hovertemplate=(
            "Minutes: %{x}<br>"
            "Points: %{y}<extra></extra>"
        )
    )
    st.plotly_chart(fig_scatter,use_container_width=True)

with log_tab:
    st.divider()
    st.subheader("Game Log")

    table_df = df.copy()

    table_df["HOME_AWAY"] = table_df["MATCHUP"].apply(lambda x: "Away" if "@" in str(x) else "Home")

    preferred_cols = [
        "GAME_DATE", "SEASON_ID", "MATCHUP", "HOME_AWAY", "WL",
        "MIN", "PTS", "AST", "REB",
        "FGM", "FGA", "FG3M", "FG3A",
        "FTM", "FTA",
        "OREB", "DREB",
        "TOV", "PF", "PLUS_MINUS"
    ]

    display_cols = [c for c in preferred_cols if c in table_df.columns]
    with st.expander("Customize columns"):
        selected_cols = st.multiselect(
            "Columns to display",
            options=display_cols,
            default=display_cols
        )
        
    table_df = table_df.sort_values("GAME_DATE")
    st.caption(f"{len(table_df)} games shown")
    st.dataframe(
        table_df[selected_cols],
        use_container_width=True,
        height=420
    )