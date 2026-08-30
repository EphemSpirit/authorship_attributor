from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.extensions import engine, Base
from app.routers.authors_router import router as authors_router
from app.routers.documents_router import router as documents_router
import os

load_dotenv()

def create_app():
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.getenv("FRONTEND_URL")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    Base.metadata.create_all(bind=engine)

    app.include_router(authors_router)
    app.include_router(documents_router)

    return app