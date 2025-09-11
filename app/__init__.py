from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.startup import lifespan
from app.api import root_routes, webhook_routes


def create_app() -> FastAPI:
    app = FastAPI(title="WhatsApp RAG Bot", lifespan=lifespan)
    app.include_router(root_routes.router)
    app.include_router(webhook_routes.router)

    return app
