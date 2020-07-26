from datetime import datetime, timezone, date, time, timedelta

from humtemp.configuration import settings
settings.humtemp_redis_host = 'localhost'

from fastapi.testclient import TestClient

from humtemp.main import app
from humtemp.database import connection, connect

client = TestClient(app)


def setup_function():
    connect(host='localhost')
    connection.flushdb()


def test_calculation():
    yesterday = datetime.combine(date.today() - timedelta(days=1), time.min, tzinfo=timezone.utc)
    yesterday_ts = int(yesterday.timestamp())

    timestamp = yesterday_ts
    for i in range(10):
        data = {
            "lab_id": "lab01",
            "timestamp": timestamp,
            "temp": i+1,
            "humidity": 10+i+1
        }

        response = client.post('/observation', json=data)
        assert response.status_code == 200

        timestamp += 30

    response = client.get('/summary')
    assert response.status_code == 200
    assert response.json() == [{'lab_id': 'lab01', 'avg_temp': 5.5, 'avg_humidity': 15.5}]

    response = client.get('/summary', params={'offset': 0})
    assert response.status_code == 200
    assert response.json() == []

    response = client.get('/summary', params={'offset': -2})
    assert response.status_code == 200
    assert response.json() == []
