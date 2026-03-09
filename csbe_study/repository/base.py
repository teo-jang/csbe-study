from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# MySQL 연결 정보 (docker-compose.yml의 csbe-mysql 컨테이너)
MYSQL_USER = "root"
MYSQL_PASSWORD = "csbe"
MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_DB = "csbe_study"

SYNC_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
ASYNC_URL = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"


class BaseRepository:
    def __init__(self):
        self.engine = create_engine(
            SYNC_URL,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
        )
        self.async_engine = create_async_engine(
            ASYNC_URL,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
        )

        self.AsyncSession = sessionmaker(
            bind=self.async_engine, class_=AsyncSession, expire_on_commit=False
        )

    def create_table(self):
        with self.engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS images (id INT AUTO_INCREMENT PRIMARY KEY, image_path VARCHAR(512), INDEX idx_image_path (image_path))"
                )
            )
            conn.commit()

    async def create_table_async(self):
        async with self.async_engine.begin() as conn:
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS images (id INT AUTO_INCREMENT PRIMARY KEY, image_path VARCHAR(512), INDEX idx_image_path (image_path))"
                )
            )

    def insert_sync(self, image_path):
        with self.engine.begin() as conn:
            for _ in range(5):
                conn.execute(
                    text("INSERT INTO images(image_path) VALUES(:image_path)"),
                    image_path,
                )
                conn.execute(
                    text("DELETE FROM images WHERE image_path = :image_path"),
                    image_path,
                )

            conn.execute(
                text("INSERT INTO images(image_path) VALUES(:image_path)"), image_path
            )

    async def insert_async(self, image_path):
        async with self.AsyncSession() as session:
            async with session.begin():
                for _ in range(5):
                    await session.execute(
                        text("INSERT INTO images(image_path) VALUES(:image_path)"),
                        image_path,
                    ),
                    await session.execute(
                        text("DELETE FROM images WHERE image_path = :image_path"),
                        image_path,
                    )

                await session.execute(
                    text("INSERT INTO images(image_path) VALUES(:image_path)"),
                    image_path,
                )
