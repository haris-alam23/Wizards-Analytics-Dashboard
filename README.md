# Washington Wizards Analytics Dashboard

This project is an end-to-end data pipeline & analytics dashboard built around Washington Wizards player game data. It combines a structured ETL pipeline, a PostgreSQL database, an interactive Streamlit app, and a simple machine learning model for next game point prediction.

## What this project does

- Extracts, transforms, and loads Wizards player game data using a modular ETL pipeline
- Stores cleaned data in a PostgreSQL database
- Uses SQL queries to retrieve player and game level data
- Displays interactive analytics in a multi page Streamlit dashboard
- Generates a simple prediction for a player’s points in their next game

## Tech stack

- Python  
- PostgreSQL  
- Pandas  
- SQLAlchemy  
- Streamlit  
- Plotly  
- scikit learn  

## Project structure

```text
wizards-frontoffice/
│
├── app/                        # Streamlit application
│   ├── pages/
│   │   ├── 1_Home.py           # Main dashboard page
│   │   └── 2_Predictions.py    # Prediction page
│   ├── models/
│   │   └── points_next_model.joblib
│   ├── db.py                   # Database connection logic
│   ├── queries.py              # SQL queries used by the app
│   └── prediction.py           # Feature preparation and inference logic
│
├── src/                        # ETL pipeline
│   ├── extract.py              # Data extraction
│   ├── transform.py            # Data cleaning and transformation
│   └── load.py                 # Load data into PostgreSQL
│
├── data/
│   ├── raw/                    # Raw input data
│   └── processed/              # Cleaned datasets
│
├── notebooks/                  # Exploration and development notebooks
├── requirements.txt
└── README.md
```
## Features
- ETL pipeline with separate extract, transform, and load steps
- Relational database storing player game logs
- Interactive player level analytics and performance trends
- Multi page Streamlit dashboard
- Simple next game points prediction based on recent performance
- Wizards themed user interface

## Limitations
- The prediction model is intentionally simple and only predicts points
- Predictions rely on historical performance and do not account for injuries, matchups, or rotations
- Data ingestion is manually triggered and not scheduled
- The dashboard is designed for learning and exploration rather than production use

## Future improvements
- Add predictions for additional statistics such as assists and rebounds
- Incorporate opponent and matchup context into the model
- Automate ETL execution with scheduled jobs
- Add player comparison and season summary views
- Deploy the dashboard to a cloud platform
