import asyncio

from fastapi import FastAPI

from routers import printer, memory, concurrency, network, datastructure
from routers import uploader  # Ch.3 (CPU Bound vs I/O Bound) 에서 사용

# from routers import data

app = FastAPI()

app.include_router(printer.router)
app.include_router(memory.router)
app.include_router(uploader.router)
app.include_router(concurrency.router)
app.include_router(network.router)
app.include_router(datastructure.router)
# app.include_router(data.router)


@app.get("/")
async def root():
    return {"Hello": "World"}
