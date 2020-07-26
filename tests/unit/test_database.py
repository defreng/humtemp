from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from humtemp.database import connect, BucketRepository
from humtemp.dto.observation import Observation
from humtemp.entities import BucketKey


@patch('humtemp.database.Redis')
def test_connect(redis):
    connect(host='myhost', port=1, db=0)
    assert redis.called

    repo = BucketRepository()
    assert repo.connection == redis.return_value

    custom_redis = Mock()
    repo = BucketRepository(redis=custom_redis)
    assert repo.connection == custom_redis


@patch('humtemp.database.datetime')
def test_find_completed(dt):
    redis = Mock()

    bucket_offset = datetime(2020, 1, 1, 23, 0, 0, tzinfo=timezone.utc)
    bucket_offset_ts = int(bucket_offset.timestamp())

    bucket_duration = timedelta(days=1)
    repo = BucketRepository(bucket_offset=bucket_offset, bucket_duration=bucket_duration, redis=redis)

    day_seconds = 60*60*24
    redis.scan_iter = Mock(return_value=[
        f'bucket:lab01:{bucket_offset_ts + day_seconds}'.encode('utf8'),
        f'bucket:lab01:{bucket_offset_ts}'.encode('utf8'),
        f'bucket:lab01:{bucket_offset_ts - day_seconds}'.encode('utf8'),
        f'bucket:lab01:{bucket_offset_ts - 2*day_seconds}'.encode('utf8'),
        f'bucket:lab02:{bucket_offset_ts - 2*day_seconds}'.encode('utf8'),
        f'bucket:lab03:{bucket_offset_ts}'.encode('utf8'),
        f'bucket:lab03:{bucket_offset_ts - day_seconds}'.encode('utf8'),
    ])

    dt.now.return_value = datetime(2020, 1, 2, 2, 0, 0, tzinfo=timezone.utc)

    result = list(repo.find_in_bucket(-1))
    assert len(result) == 2
    assert f'bucket:lab01:{bucket_offset_ts - day_seconds}' in result
    assert f'bucket:lab03:{bucket_offset_ts - day_seconds}' in result

    dt.now.return_value = datetime(2020, 1, 1, 23, 0, 0, tzinfo=timezone.utc)

    result = list(repo.find_in_bucket(-1))
    assert len(result) == 2
    assert f'bucket:lab01:{bucket_offset_ts - day_seconds}' in result
    assert f'bucket:lab03:{bucket_offset_ts - day_seconds}' in result


def test_get():
    redis = Mock()
    repo = BucketRepository(redis=redis)

    redis.hgetall.return_value = {b'num_observations': b'1', b'sum_temp': b'22.8', b'sum_humidity': b'23'}

    entity = repo.get(BucketKey('dummy'))
    assert entity.num_observations == 1
    assert entity.sum_temp == 22.8
    assert entity.sum_humidity == 23

    redis.hgetall.return_value = None
    assert repo.get(BucketKey('dummy')) is None


def test_add_observation():
    redis = Mock()
    repo = BucketRepository(redis=redis)

    pipeline = redis.pipeline.return_value

    observation_ts = int(datetime(2020, 1, 1, 3, 0, 30, tzinfo=timezone.utc).timestamp())
    repo.add_observation(Observation(
        lab_id='lab01',
        timestamp=observation_ts,
        temp=23.1,
        humidity=40.2
    ))

    bucket_ts = int(datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp())

    assert pipeline.hincrby.call_args.args == (f'bucket:lab01:{bucket_ts}', 'num_observations', 1)
    assert pipeline.hincrbyfloat.called
    assert pipeline.expireat.called
    assert pipeline.execute.called


def test__get_bucket_start():
    bucket_offset = datetime(2020, 1, 1, 23, 0, 0, tzinfo=timezone.utc)
    bucket_offset_ts = int(bucket_offset.timestamp())

    bucket_duration = timedelta(days=1)
    repo = BucketRepository(bucket_offset=bucket_offset, bucket_duration=bucket_duration, redis=Mock())

    assert repo._get_bucket_start(bucket_offset_ts - 1) == bucket_offset_ts - int(bucket_duration.total_seconds())
    assert repo._get_bucket_start(bucket_offset_ts) == bucket_offset_ts
    assert repo._get_bucket_start(bucket_offset_ts + 1) == bucket_offset_ts
    assert repo._get_bucket_start(bucket_offset_ts + 60*60) == bucket_offset_ts
    assert repo._get_bucket_start(bucket_offset_ts + 60*60*24 - 1) == bucket_offset_ts

    bucket_duration = timedelta(seconds=1)
    repo = BucketRepository(bucket_offset=bucket_offset, bucket_duration=bucket_duration, redis=Mock())

    assert repo._get_bucket_start(bucket_offset_ts) == bucket_offset_ts
    assert repo._get_bucket_start(bucket_offset_ts + 1) == bucket_offset_ts + 1


@patch('humtemp.database.datetime')
def test__timestamp_is_in_bucket(dt):
    bucket_offset = datetime(2020, 1, 1, 23, 0, 0, tzinfo=timezone.utc)
    bucket_offset_ts = int(bucket_offset.timestamp())

    bucket_duration = timedelta(days=1)
    bucket_duration_seconds = int(bucket_duration.total_seconds())
    repo = BucketRepository(bucket_offset=bucket_offset, bucket_duration=bucket_duration, redis=Mock())

    dt.now.return_value = datetime(2020, 1, 1, 23, 0, 0, tzinfo=timezone.utc)

    assert repo._timestamp_is_in_bucket(bucket_offset_ts)
    assert not repo._timestamp_is_in_bucket(bucket_offset_ts, offset=-1)
    assert not repo._timestamp_is_in_bucket(bucket_offset_ts, offset=1)

    assert repo._timestamp_is_in_bucket(bucket_offset_ts + 1)
    assert not repo._timestamp_is_in_bucket(bucket_offset_ts + bucket_duration_seconds)
    assert not repo._timestamp_is_in_bucket(bucket_offset_ts - 1)
