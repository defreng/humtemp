from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from fastapi.testclient import TestClient

from humtemp import database
from humtemp.entities import BucketEntity, BucketKey
from humtemp.main import app, _get_repository

database.connection = Mock()

client = TestClient(app)
mock_bucket_repo = None


class MockBucketRepository:
    add_observation: Mock

    def __init__(self):
        self.add_observation = Mock()
        self.buckets = {
            0: [
                BucketEntity(key=BucketKey('bucket:lab01:111111')),
                BucketEntity(key=BucketKey('bucket:lab02:111111')),
                BucketEntity(key=BucketKey('bucket:lab03:111111')),
            ],
            -1: [
                BucketEntity(key=BucketKey('bucket:lab01:111110'), num_observations=2, sum_temp=40.0),
                BucketEntity(key=BucketKey('bucket:lab02:111110')),
                BucketEntity(key=BucketKey('bucket:lab03:111110')),
            ],
        }

    def find_in_bucket(self, offset: int = 0):
        if offset not in self.buckets:
            return []

        return list([entity.key for entity in self.buckets[offset]])

    def get(self, key: BucketKey):
        for bucket_list in self.buckets.values():
            for entity in bucket_list:
                if entity.key == key:
                    return entity


class TestObservationPost:
    def setup_method(self):
        self.client = TestClient(app)
        self.mock_bucket_repo = MockBucketRepository()

        app.dependency_overrides[_get_repository] = lambda: self.mock_bucket_repo

    def teardown_method(self):
        app.dependency_overrides = {}

    def test_observation_post_invalid(self):
        response = client.post('/observation')
        assert response.status_code == 422

        response = client.post('/observation', json={
            "lab_id": "",
            "timestamp": int(datetime(2020, 2, 1, 0, 30, 30, tzinfo=timezone.utc).timestamp()),
            "temp": 23.4,
            "humidity": 50.1
        })
        assert response.status_code == 422

        response = client.post('/observation', json={
            "lab_id": "a"*60,
            "timestamp": int(datetime(2020, 2, 1, 0, 30, 30, tzinfo=timezone.utc).timestamp()),
            "temp": 23.4,
            "humidity": 50.1
        })
        assert response.status_code == 422

        response = client.post('/observation', json={
            "lab_id": "myroom:1",
            "timestamp": int(datetime(2020, 2, 1, 0, 30, 30, tzinfo=timezone.utc).timestamp()),
            "temp": 23.4,
            "humidity": 50.1
        })
        assert response.status_code == 422

        response = client.post('/observation', json={
            "lab_id": "validlab",
            "timestamp": int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp()),
            "temp": 23.4,
            "humidity": 50.1
        })
        assert response.status_code == 422

    def test_observation_post_valid(self):
        response = client.post('/observation', json={
            "lab_id": "validlab",
            "timestamp": int(datetime(2020, 2, 1, 0, 30, 30, tzinfo=timezone.utc).timestamp()),
            "temp": 23.4,
            "humidity": 50.1
        })
        assert response.status_code == 200
        assert self.mock_bucket_repo.add_observation.called


class TestSummaryGet:
    def setup_method(self):
        self.client = TestClient(app)
        self.mock_bucket_repo = MockBucketRepository()

        app.dependency_overrides[_get_repository] = lambda: self.mock_bucket_repo

    def test_summary_bare(self):
        response = self.client.get('/summary')
        assert response.status_code == 200

        for summary in response.json():
            if summary['lab_id'] == 'lab01':
                assert summary['avg_temp'] == 20.0
            else:
                assert summary['avg_temp'] == 0

            assert summary['avg_humidity'] == 0

    def test_summary_empty_result(self):
        response = self.client.get('/summary', params={'offset': -2})
        assert response.status_code == 200
        assert len(response.json()) == 0

