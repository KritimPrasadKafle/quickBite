# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.log_config import configure_logging
from core.middleware import RequestIDMiddleware
from modules.users.router import router as user_router
from shared.base_schema import APIResponse
configure_logging()

app = FastAPI(title="QuickBite API", version="1.0.0")

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router, prefix="/api/v1/auth", tags=["auth"])

@app.get("/health", response_model=APIResponse, tags=["health"])
async def health():
    return APIResponse(
        message="QuickBite API is running",
        status_code=200,
    )