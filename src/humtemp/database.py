from datetime import datetime, timedelta
from typing import *

from redis import Redis

from humtemp.configuration import settings
from humtemp.dto.observation import Observation
from humtemp.entities import BucketEntity, BucketKey

connection: Optional[Redis] = None


def connect(host: str = 'localhost', port: int = 6379, db: int = 0) -> None:
    global connection
    connection = Redis(host=host, port=port, db=db, encoding='utf8')


class BucketRepository:
    def __init__(self,
                 bucket_offset: datetime = settings.bucket_offset,
                 bucket_duration: timedelta = settings.bucket_duration,
                 bucket_retention: int = settings.humtemp_bucket_retention,

                 redis: Optional[Redis] = None):
        self.prefix = 'bucket'

        if redis is None:
            redis = connection
        if redis is None:
            raise ValueError('connection to redis is not yet initialized')

        self.connection: Redis = redis

        if bucket_offset.utcoffset() is None:
            raise ValueError('"bucket_offset" must be given a timezone-aware datetime object')

        self.bucket_offset = int(bucket_offset.timestamp())
        self.bucket_duration = int(bucket_duration.total_seconds())
        self.bucket_retention = bucket_retention

    def add_observation(self, observation: Observation) -> None:
        observation_bucket_start = self._get_bucket_start(observation.timestamp)
        key = BucketEntity.construct_key(observation.lab_id, observation_bucket_start)

        pipe = self.connection.pipeline()

        pipe.hincrby(key, 'num_observations', 1)
        pipe.hincrbyfloat(key, 'sum_temp', observation.temp)
        pipe.hincrbyfloat(key, 'sum_humidity', observation.humidity)

        pipe.expireat(key, observation_bucket_start + self.bucket_retention * self.bucket_duration)

        pipe.execute()

    def find_in_bucket(self, offset: int = 0) -> Iterable[BucketKey]:
        keys = self.connection.scan_iter(match=f'{self.prefix}:*')
        deconstructed_keys = map(BucketEntity.deconstruct_key, keys)
        deconstructed_keys = filter(lambda x: self._timestamp_is_in_bucket(x[1], offset), deconstructed_keys)
        keys = map(lambda x: BucketEntity.construct_key(*x), deconstructed_keys)

        return keys

    def get(self, key: BucketKey) -> Optional[BucketEntity]:
        data = self.connection.hgetall(key)

        if data is None:
            return

        return BucketEntity(
            key=key,
            num_observations=data[b'num_observations'],
            sum_temp=data[b'sum_temp'],
            sum_humidity=data[b'sum_humidity']
        )

    def _timestamp_is_in_bucket(self, timestamp, offset: int = 0):
        current_bucket_start = self._get_bucket_start()

        bucket_start = current_bucket_start + offset * self.bucket_duration
        bucket_end = bucket_start + self.bucket_duration

        return bucket_start <= timestamp < bucket_end

    def _get_bucket_start(self, timestamp: Optional[int] = None) -> int:
        if timestamp is None:
            timestamp = int(datetime.now().timestamp())

        start_from_offset = ((timestamp - self.bucket_offset) // self.bucket_duration) * self.bucket_duration
        return self.bucket_offset + start_from_offset
