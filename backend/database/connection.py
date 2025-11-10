import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

if __name__ == "__main__":
    try:
        conn = engine.connect()
        print("✅ Conexão com o banco estabelecida com sucesso!")
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao conectar no banco: {e}")