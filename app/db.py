import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def get_engine():
    
    
    url =  os.environ.get("DATABASE_URL")
    
    if not url:
        raise RuntimeError("DATABASE_URL not set. ")
    
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    print("DB host:", url.split("@")[1].split("/")[0])

    return create_engine(url, pool_pre_ping= True)

