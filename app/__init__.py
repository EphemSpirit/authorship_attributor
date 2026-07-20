from dotenv import load_dotenv
from fastapi import FastAPI
from app.extensions import engine, Base
from app.routers.authors_router import router as authors_router

load_dotenv()

def create_app():
    app = FastAPI()

    Base.metadata.create_all(bind=engine)

    app.include_router(authors_router)

    return app