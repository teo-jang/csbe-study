import asyncio  # Ch.3 (CPU Bound vs I/O Bound) 에서 사용

from fastapi import APIRouter

router = APIRouter(prefix="/print", tags=["print"])


@router.get("/doPrint/{message}")
def print_sync(message: str):
    ret = ""
    for _ in range(100):
        for i in range(len(message)):
            ret += message[i]
            print(message[i])

    return {"message": ret}


@router.get("/dontPrint/{message}")
def return_sync(message: str):
    ret = ""
    for _ in range(100):
        for i in range(len(message)):
            ret += message[i]

    return {"message": ret}


@router.get("/doPrintAsync/{message}")
async def print_async(message: str):
    async def async_print(message: str):
        await asyncio.sleep(0)
        print(message)

    ret = ""
    for _ in range(100):
        for i in range(len(message)):
            ret += message[i]
            await async_print(message[i])

    return {"message": ret}
