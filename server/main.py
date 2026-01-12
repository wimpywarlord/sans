from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from brain.utils.logger import logger
from routers.chat import router as chat_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up FastAPI server...")
    yield
    logger.info("Shutting down FastAPI server...")


app = FastAPI(
    title="Server API",
    description="FastAPI backend server",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)


@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Hello from FastAPI"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
