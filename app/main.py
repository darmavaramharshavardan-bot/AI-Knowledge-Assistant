from fastapi import FastAPI

from app.database import engine, Base
from app import models

from app.routers.chat import router as chat_router
from app.routers.auth import router as auth_router
from app.routers.documents import router as documents_router


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="AI Knowledge Assistant",
    description="AI-powered knowledge assistant",
    version="1.0.0"
)


# Register routers
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(documents_router)


@app.get("/")
def home():
    return {
        "message": "AI Knowledge Assistant is running"
    }