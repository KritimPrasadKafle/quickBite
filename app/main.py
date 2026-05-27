# app/main.py
from fastapi import FastAPI
from modules.users.router import router as user_router

app = FastAPI()

app.include_router(user_router, prefix="/auth", tags=["auth"])