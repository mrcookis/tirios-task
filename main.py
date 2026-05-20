from fastapi import FastAPI

from app.api.routes.health import router as health_router

app = FastAPI(title="Tomek Tirios Task")

app.include_router(health_router)