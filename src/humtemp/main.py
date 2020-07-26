from typing import *

from fastapi import FastAPI, Depends

from humtemp.configuration import settings
from humtemp.database import BucketRepository, connect
from humtemp.dto import Observation, Summary


connect(
    host=settings.humtemp_redis_host,
    port=settings.humtemp_redis_port,
    db=settings.humtemp_redis_db
)
app = FastAPI()


async def _get_repository() -> BucketRepository:
    return BucketRepository(
        bucket_offset=settings.bucket_offset,
        bucket_duration=settings.bucket_duration
    )


@app.post('/observation')
async def observation(
        data: Observation,
        repo: BucketRepository = Depends(_get_repository)):
    repo.add_observation(data)


@app.get('/summary', response_model=List[Summary])
async def summary(
        offset: int = -1,
        repo: BucketRepository = Depends(_get_repository)) -> List[Summary]:
    result = []
    for key in repo.find_in_bucket(offset=offset):
        entity = repo.get(key)
        if entity is None:
            continue

        result.append(Summary(
            lab_id=entity.lab_id,
            avg_temp=entity.avg_temp,
            avg_humidity=entity.avg_humidity
        ))

    return result
