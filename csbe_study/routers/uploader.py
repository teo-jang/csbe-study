import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from fastapi import APIRouter, UploadFile, File, BackgroundTasks

from repository.base import BaseRepository
from service.image import ImageProcessor

router = APIRouter(prefix="/commiter", tags=["commit"])

baseRepository = BaseRepository()

# 요청마다 생성하면 오버헤드가 크다. 앱 레벨에서 한 번만 생성해서 재사용한다.
thread_executor = ThreadPoolExecutor()
process_executor = ProcessPoolExecutor()


@router.on_event("startup")
async def on_startup():
    baseRepository.create_table()
    await baseRepository.create_table_async()


def _save_image(file: UploadFile) -> tuple[str, str]:
    filename, file_extension = os.path.splitext(file.filename)
    generated_id = uuid.uuid4()
    image_path = f"tmp/{generated_id}{filename}{file_extension}"
    output_path = f"tmp/{generated_id}{file_extension}"

    with open(image_path, "wb") as f:
        f.write(file.file.read())

    return image_path, output_path


# 1. 동기 처리: def 핸들러 → FastAPI가 자동으로 threadpool에서 실행한다
@router.post("/upload_sync")
def upload_sync(file: UploadFile = File(...)):
    image_path, output_path = _save_image(file)

    ImageProcessor.convert_image(image_path, output_path)
    baseRepository.insert_sync({"image_path": output_path})

    return {"image_path": image_path, "output_path": output_path}


# 2. asyncio 처리: async def인데 CPU 작업을 그대로 실행 → 이벤트 루프를 블로킹한다
@router.post("/upload_asyncio")
async def upload_asyncio(file: UploadFile = File(...)):
    image_path, output_path = _save_image(file)

    try:
        await asyncio.gather(
            ImageProcessor.convert_image_async(image_path, output_path),
            baseRepository.insert_async({"image_path": output_path}),
        )
    except Exception as e:
        return {"error": str(e)}

    return {"image_path": image_path, "output_path": output_path}


# 3. ThreadPool 처리: CPU 작업을 스레드로 보내지만, GIL 때문에 진짜 병렬 실행은 안 된다
@router.post("/upload_threadpool")
async def upload_threadpool(file: UploadFile = File(...)):
    image_path, output_path = _save_image(file)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        thread_executor, ImageProcessor.convert_image, image_path, output_path
    )
    await loop.run_in_executor(
        thread_executor, baseRepository.insert_sync, {"image_path": output_path}
    )

    return {"image_path": image_path, "output_path": output_path}


# 4. ProcessPool 처리: CPU 작업을 별도 프로세스로 보낸다 → GIL 우회
@router.post("/upload_processpool")
async def upload_processpool(file: UploadFile = File(...)):
    image_path, output_path = _save_image(file)

    # CPU Bound 작업(이미지 처리)만 ProcessPool로 보낸다
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        process_executor, ImageProcessor.convert_image, image_path, output_path
    )

    # I/O Bound 작업(DB)은 메인 프로세스에서 처리한다
    baseRepository.insert_sync({"image_path": output_path})

    return {"image_path": image_path, "output_path": output_path}


# 5. 하이브리드: CPU는 ProcessPool, I/O는 async (실무 권장 패턴)
@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    image_path, output_path = _save_image(file)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        process_executor, ImageProcessor.convert_image, image_path, output_path
    )

    await baseRepository.insert_async({"image_path": output_path})

    return {"image_path": image_path, "output_path": output_path}


# 6. BackgroundTask: 응답을 먼저 보내고, 이미지 처리+DB는 백그라운드에서
async def process_image_and_save(image_path: str, output_path: str):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        process_executor, ImageProcessor.convert_image, image_path, output_path
    )

    await baseRepository.insert_async({"image_path": output_path})


@router.post("/upload_background_task")
async def upload_background_task(
    file: UploadFile = File(...), background_tasks: BackgroundTasks = None
):
    image_path, output_path = _save_image(file)

    background_tasks.add_task(process_image_and_save, image_path, output_path)

    return {"image_path": image_path, "output_path": output_path}
