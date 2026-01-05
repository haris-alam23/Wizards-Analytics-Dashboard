from __future__ import annotations
import joblib
import pandas as pd
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from db import get_engine


@dataclass(frozen=True)
class Config:
    table: str = "wizards.player_games"
    outpath: str = "models/points_next_model.joblib"
    test_frac: float = 0.2
    window_short: int = 5
    window_long: int = 10


def rmse(y_true, y_pred) -> float:
    return float(mean_squared_error(y_true, y_pred) ** 0.5)


def load_data() -> pd.DataFrame:
    engine = get_engine()
    df = pd.read_sql(f"SELECT * FROM {Config.table}", engine)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    return df


def target_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    df = df.copy()

    df["is_home"] = (
        df["MATCHUP"].str.contains("vs", case=False, na=False).astype(int)
        if "MATCHUP" in df.columns
        else 0
    )

    df = df.sort_values(["PLAYER_ID", "GAME_DATE", "GAME_ID"]).reset_index(drop=True)

    df["days_rest"] = df.groupby("PLAYER_ID")["GAME_DATE"].diff().dt.days
    df["days_rest"] = df["days_rest"].clip(lower=0).fillna(0)
    df["PTS_next"] = df.groupby("PLAYER_ID")["PTS"].shift(-1)

    grp = df.groupby("PLAYER_ID", group_keys=False)

    roll_map = {
        "PTS": "pts_avg",
        "MIN": "min_avg",
        "FGA": "fga_avg",
        "AST": "ast_avg",
        "REB": "reb_avg",
    }

    feature_cols: list[str] = []
    for col, prefix in roll_map.items():
        name = f"{prefix}_{Config.window_short}"
        df[name] = grp[col].rolling(Config.window_short).mean().reset_index(level=0, drop=True)
        feature_cols.append(name)

    std_name = f"pts_std_{Config.window_short}"
    df[std_name] = grp["PTS"].rolling(Config.window_short).std().reset_index(level=0, drop=True)
    feature_cols.append(std_name)

    long_name = f"pts_avg_{Config.window_long}"
    df[long_name] = grp["PTS"].rolling(Config.window_long).mean().reset_index(level=0, drop=True)

    trend_name = "pts_trend_short_vs_long"
    df[trend_name] = df[f"pts_avg_{Config.window_short}"] - df[long_name]
    feature_cols.append(trend_name)

    feature_cols.append("is_home")
    feature_cols.append("days_rest")

    return df, feature_cols


def time_split(df_model: pd.DataFrame, feature_cols: list[str]):
    df_model = df_model.sort_values(["GAME_DATE", "PLAYER_ID", "GAME_ID"]).reset_index(drop=True)

    X = df_model[feature_cols]
    y = df_model["PTS_next"]

    split = int(len(df_model) * (1 - Config.test_frac))
    return X.iloc[:split], X.iloc[split:], y.iloc[:split], y.iloc[split:], df_model


def score_model(model, X_train, y_train, X_test, y_test) -> dict[str, float]:
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    return {
        "mae": float(mean_absolute_error(y_test, preds)),
        "rmse": rmse(y_test, preds),
    }


def main() -> None:
    df = load_data()
    df, feature_cols = target_features(df)

    feature_cols = [
        f"fga_avg_{Config.window_short}",
        f"min_avg_{Config.window_short}",
        f"pts_std_{Config.window_short}",
        "is_home",
        "days_rest",
    ]

    df_model = df.dropna(subset=feature_cols + [f"pts_avg_{Config.window_short}", "PTS_next"]).copy()
    if df_model.empty:
        raise RuntimeError("No training rows after feature engineering (need >=10 games per player).")

    X_train, X_test, y_train, y_test, df_model = time_split(df_model, feature_cols)


    baseline_prediction = df_model.loc[X_test.index, f"pts_avg_{Config.window_short}"]
    print("Baseline:", {
        "mae": float(mean_absolute_error(y_test, baseline_prediction)),
        "rmse": rmse(y_test, baseline_prediction),
    })

    linear = LinearRegression()
    linear_metrics = score_model(linear, X_train, y_train, X_test, y_test)

    print("LinearRegression:", linear_metrics)
    coef = pd.Series(linear.coef_, index=feature_cols).sort_values(key=abs, ascending=False)
    print("\n=== LR Coefficients ===")
    print(coef.to_string())
    print("Intercept:", float(linear.intercept_))

    outpath = Path(Config.outpath)
    outpath.parent.mkdir(parents=True, exist_ok=True)

    artifact: dict[str, Any] = {
        "model_name": "linear_regression",
        "metrics": linear_metrics,
        "feature_cols": feature_cols,  
        "target_col": "PTS_next",
        "short_window": Config.window_short,
        "long_window": Config.window_long,
        "model": linear,
    }
    joblib.dump(artifact, outpath)
    print(f"\n✅ Saved model to {outpath}")

    
    latest = (
        df.dropna(subset=feature_cols)
          .sort_values(["PLAYER_ID", "GAME_DATE", "GAME_ID"])
          .groupby("PLAYER_ID")
          .tail(1)
    )
    preds = linear.predict(latest[feature_cols])

    latest_out = latest[["PLAYER_ID", "PLAYER_NAME", "GAME_DATE"]].copy() if "PLAYER_NAME" in latest.columns else latest[["PLAYER_ID", "GAME_DATE"]].copy()
    latest_out["PTS_pred_next"] = preds

    top1 = latest_out.sort_values("PTS_pred_next", ascending=False).head(1)
    pid = int(top1["PLAYER_ID"].iloc[0])
    pname = top1["PLAYER_NAME"].iloc[0] if "PLAYER_NAME" in top1.columns else str(pid)

    one_row = latest[latest["PLAYER_ID"] == pid].copy()
    print(f"\n=== Sanity check: {pname} ({pid}) ===")
    print(one_row[["GAME_DATE"] + feature_cols].to_string(index=False))
    print("Predicted PTS_next:", float(top1["PTS_pred_next"].iloc[0]))

    print("\nTop 10 predicted next-game scorers:")
    print(latest_out.sort_values("PTS_pred_next", ascending=False).head(10).to_string(index=False))


if __name__ == "__main__":
    main()
