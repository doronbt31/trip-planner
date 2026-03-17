from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.config import load_trip
from src.routes import chat, docs, gallery, home, itinerary, map, trip, weather
from src.routes.docs import api_router as docs_api_router
from src.routes.docs import router as docs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_trip()  # validate trip.yaml is readable on startup
    yield


app = FastAPI(title="Trip Planner", lifespan=lifespan, docs_url="/api/swagger", redoc_url="/api/redoc")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(home.router)
app.include_router(trip.router, prefix="/api")
app.include_router(docs_api_router, prefix="/api")
app.include_router(docs_router)
app.include_router(map.router)
app.include_router(itinerary.router)
app.include_router(gallery.router)
app.include_router(weather.router, prefix="/api")
app.include_router(chat.router)
