import sys
from functools import cache
from typing import Dict

from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from csbe_study.model.TrafficInfo import TrafficInfo


class TrafficInfoRepository:
    def __init__(self):
        self.async_engine = create_async_engine(
            "mysql+aiomysql://root:12345678!@localhost:55001/" "csbe?charset=utf8"
        )

        self.AsyncSession = sessionmaker(
            bind=self.async_engine, class_=AsyncSession, expire_on_commit=False
        )

    @cache
    async def get_all(self) -> Dict[str, TrafficInfo]:
        ret = {}
        offset = 0
        batch_size = 1000
        async with self.AsyncSession() as session:
            while True:
                async with session.begin():
                    query = select(TrafficInfo).offset(offset).limit(batch_size)
                    result = await session.execute(query)
                    rows = result.scalars().all()

                    if not rows:
                        break

                    for r in rows:
                        key = f"{r.transportation_date}_{r.line_name}_{r.station_name}_{r.division_name}"
                        ret[key] = r

                    offset += batch_size

        print(f"data size:{sys.getsizeof(ret)}")
        return ret

    async def get_one(
        self,
        transportation_date: str,
        line_name: str,
        station_name: str,
        division_name: str,
    ) -> TrafficInfo:
        async with self.AsyncSession.begin() as session:
            query = select(TrafficInfo).filter_by(
                transportation_date=transportation_date,
                line_name=line_name,
                station_name=station_name,
                division_name=division_name,
            )

            # print(query.compile(compile_kwargs={"literal_binds": True}))

            result = await session.execute(query)
            ret = result.scalar_one_or_none()
            # print(f"result:{ret}")
            return ret
