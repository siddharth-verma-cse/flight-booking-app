import logging

from fastapi import FastAPI
from contextlib import asynccontextmanager
from .routers import flights

from .routers import users
from .crud.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(flights.router)


@app.get("/")
def read_root():
    return {"message": "Flight booking API!"}
