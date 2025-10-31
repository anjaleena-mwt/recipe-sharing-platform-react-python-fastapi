from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

db_url = "postgresql://postgres:askr@localhost:5432/RecipeRealm" 
engine = create_engine(db_url, future=True) 
session = sessionmaker(autocommit=False, autoflush=False, bind=engine) 
