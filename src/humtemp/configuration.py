from datetime import datetime, timedelta

from pydantic import BaseSettings


class Settings(BaseSettings):
    # redis database connection parameters
    humtemp_redis_host: str = 'localhost'
    humtemp_redis_port: int = 6379
    humtemp_redis_db: int = 0

    # humtemp divides the time into buckets. Bucket boundaries will be aligned to this offset
    humtemp_bucket_offset: str = '1970-01-01T00:00:00+00:00'
    # how large (in terms of duration) every bucket is in seconds
    humtemp_bucket_duration: int = 60 * 60 * 24

    # how many old buckets should be kept in the database. This number includes the "current" bucket.
    # Example "2": Keeps the currently active bucket, as well as 1 bucket in the past.
    humtemp_bucket_retention: int = 2

    @property
    def bucket_offset(self) -> datetime:
        return datetime.fromisoformat(self.humtemp_bucket_offset)

    @property
    def bucket_duration(self):
        return timedelta(seconds=self.humtemp_bucket_duration)


settings = Settings()
