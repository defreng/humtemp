import asyncio
from datetime import datetime, timedelta
import random

import aiohttp

TARGET_URL = 'http://roche-1364866895.us-east-1.elb.amazonaws.com/observation'


async def send_lab_observations(lab: str, num_requests=2880, step_seconds=30):
    temps = []
    humidities = []

    timestamp_start = int((datetime.now() - timedelta(days=1)).timestamp())

    async with aiohttp.ClientSession() as session:
        for timestamp in range(timestamp_start, timestamp_start + num_requests*step_seconds, step_seconds):
            data = {
                'lab_id': lab,
                'timestamp': timestamp,
                'temp': 20 + random.random() * 10,
                'humidity': 40 + random.random() * 20,
            }
            temps.append(data['temp'])
            humidities.append(data['humidity'])

            for i in range(3):
                async with session.post(TARGET_URL, json=data) as response:
                    if response.status == 200:
                        break
                    if response.status >= 500:
                        await asyncio.sleep(2)
                        continue

                    raise Exception(await response.text())

    print(f'{lab}: TEMP: {sum(temps) / len(temps):.3f} | HUM: {sum(humidities) / len(humidities):.3f}')


async def main():
    LABS = list([f'room{i:0>5}' for i in range(100)])
    num_requests = 2880

    coros = []
    for lab in LABS:
        coros.append(send_lab_observations(lab, num_requests=num_requests))

    start = datetime.now()
    await asyncio.gather(*coros)
    print(f'Sent {len(LABS) * num_requests} requests')
    print(f'Took: {datetime.now() - start}')

if __name__ == '__main__':
    asyncio.run(main())
