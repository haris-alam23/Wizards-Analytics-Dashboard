import streamlit as st 
import pandas as pd
import joblib
import plotly.graph_objects as go
from pathlib import Path
from prediction import load_data, target_features


st.set_page_config("Points Prediction", layout="wide")

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
Next-Game Scoring Predictions
</div>
<div style="
color: rgba(255,255,255,0.85);
font-size: 1rem;">
Predictions are based on each player’s most recent completed game.
</div>
</div>""",
unsafe_allow_html=True
)

def load_artifact():
    
    app_dir = Path(__file__).resolve().parents[1]
    model_path = app_dir / "models" / "points_next_model.joblib"


    if not model_path.is_file():
        raise FileNotFoundError(f"Expected model file at: {model_path}")

    return joblib.load(model_path)


def get_latest_predictions():
    artifact = load_artifact()
    model = artifact["model"]
    feature_cols = artifact["feature_cols"]
    
    df = load_data()
    df, _ = target_features(df)
    
    latest = (
        df.dropna(subset=feature_cols)
        .sort_values(["PLAYER_ID", "GAME_DATE", "GAME_ID"])
        .groupby("PLAYER_ID")
        .tail(1)
        .copy()
    )
    
    latest["PTS_next"] = model.predict(latest[feature_cols])
    
    cols = ["PLAYER_ID", "PLAYER_NAME", "GAME_DATE", "PTS_next"]
    if "PLAYER_NAME" not in latest.columns:
        cols.remove("PLAYER_NAME")
        
    out = latest[cols].copy()
    out = out.sort_values("PTS_next", ascending=False).reset_index(drop=True)
    out = out.rename(columns={"PTS_next": "Predicted Points", "GAME_DATE": "Based on Game Date"})
    return out, latest, feature_cols, df



try:
    artifact = load_artifact()
except Exception as e:
    st.error(f"Could not load model artifact. Error: {e}")
    st.stop()

st.caption(
    f"Model: `{artifact.get('model_name', 'unknown')}` | "
    f"MAE: {artifact.get('metrics', {}).get('mae', 'n/a')} | "
    f"RMSE: {artifact.get('metrics', {}).get('rmse', 'n/a')}"
)


top_n = st.slider("Show top N players", min_value=5, max_value=50, value=10, step=5)

preds_df, latest_df, feature_cols, df_all = get_latest_predictions()

# Table
st.subheader("Leaderboard")

display = preds_df.head(top_n).copy()

display = display[[
    "PLAYER_NAME",
    "Based on Game Date",
    "Predicted Points"
]]

display = display.rename(columns={
    "PLAYER_NAME": "Player",
    "Based on Game Date": "Based on Game Date",
    "Predicted Points": "Predicted PTS (Next Game)",
})

display["Predicted PTS (Next Game)"] = display["Predicted PTS (Next Game)"].round(1)
display["Based on Game Date"] = pd.to_datetime(
    display["Based on Game Date"]
    ).dt.date

st.dataframe(display, use_container_width=True, hide_index=True)





# Drilldown
st.subheader("Player drill-down")
name_col = "PLAYER_NAME" if "PLAYER_NAME" in preds_df.columns else "PLAYER_ID"
player_choice = st.selectbox("Select a player", preds_df[name_col].astype(str).tolist())

row = preds_df[preds_df[name_col].astype(str) == str(player_choice)].head(1)
pred_pts = float(row["Predicted Points"].iloc[0])
game_date = pd.to_datetime(row["Based on Game Date"].iloc[0]).date()

if not row.empty:
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Predicted PTS (Next Game)", f"{pred_pts:.2f}")
    with c2:
        st.metric("Based on Latest Game Date", str(game_date))

    pid = int(row["PLAYER_ID"].iloc[0])
    one = latest_df[latest_df["PLAYER_ID"] == pid].head(1)

    st.markdown("**Model inputs (from most recent game window):**")
    st.dataframe(one[feature_cols], use_container_width=True)
    
    import plotly.graph_objects as go

recent = (
    df_all[df_all["PLAYER_ID"] == pid]
    .sort_values(["GAME_DATE", "GAME_ID"])
    .tail(10)
    .copy()
)

recent["GAME_DATE"] = pd.to_datetime(recent["GAME_DATE"]).dt.strftime("%Y-%m-%d")

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=recent["GAME_DATE"],
        y=recent["PTS"],
        mode="lines+markers",
        name="Actual PTS (last 10)",
    )
)

fig.add_hline(
    y=pred_pts,
    line_dash="dash",
    line_color = "#E31837",
    annotation_text=f"Predicted next game: {pred_pts:.2f}",
    annotation_position="top left",
)

fig.update_layout(
    title="Recent scoring trend",
    xaxis_title="Game date",
    yaxis_title="Points",
    height=360,
    margin=dict(l=20, r=20, t=50, b=20),
)

st.plotly_chart(fig, use_container_width=True)

st.dataframe(
    recent[["GAME_DATE", "MATCHUP", "MIN", "FGA", "PTS"]].reset_index(drop=True),
    use_container_width=True,
    hide_index=True,
)
