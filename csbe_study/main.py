from fastapi import FastAPI

from routers import printer, memory, concurrency, network, datastructure
from routers import uploader  # Ch.3 (CPU Bound vs I/O Bound) 에서 사용
from routers import ch13_orm  # Ch.13 (ORM과 N+1)
from routers import ch14_index  # Ch.14 (인덱스)
from routers import ch15_transaction  # Ch.15 (Transaction과 Isolation Level)
from routers import ch16_tuning  # Ch.16 (DB 성능 튜닝)
from routers import ch17_cache  # Ch.17 (캐시 장애)
from routers import ch18_layered_cache  # Ch.18 (계층 캐시)
from routers import ch19_scale  # Ch.19 (Bottleneck과 Scale-Out)
from routers import ch21_order  # Ch.21 (테스트)
from routers import ch23_security  # Ch.23 (보안)

# from routers import data

app = FastAPI()

app.include_router(printer.router)
app.include_router(memory.router)
app.include_router(uploader.router)
app.include_router(concurrency.router)
app.include_router(network.router)
app.include_router(datastructure.router)
app.include_router(ch13_orm.router)
app.include_router(ch14_index.router)
app.include_router(ch15_transaction.router)
app.include_router(ch16_tuning.router)
app.include_router(ch17_cache.router)
app.include_router(ch18_layered_cache.router)
app.include_router(ch19_scale.router)
app.include_router(ch21_order.router)
app.include_router(ch23_security.router)
# app.include_router(data.router)


@app.get("/")
async def root():
    return {"Hello": "World"}
