from dotenv import load_dotenv
from fastapi import FastAPI
from app.extensions import engine, Base

load_dotenv()

def create_app():
    app = FastAPI()

    Base.metadata.create_all(bind=engine)

    return app