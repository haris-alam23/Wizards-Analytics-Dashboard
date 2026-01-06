import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def get_engine():
    
    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT")
    name = os.getenv("PGDATABASE")
    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")
    
    url =  f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
    return create_engine(url)

