import re
from datetime import datetime, timezone, timedelta
from typing import *

from pydantic import BaseModel, validator

ALLOWED_LABID_REGEX = re.compile(r'[a-zA-Z0-9/_\-.]*')
LabId = NewType('LabId', str)


class Observation(BaseModel):
    lab_id: LabId
    timestamp: int
    temp: float
    humidity: float

    @validator('lab_id')
    def lab_id_valid(cls, v: LabId) -> LabId:
        if len(v) == 0:
            raise ValueError('must not be empty')
        if len(v) > 50:
            raise ValueError('must not be longer than 50 characters')

        if not ALLOWED_LABID_REGEX.fullmatch(v):
            raise ValueError('must only contain alphanumeric characters (or / . - _)')

        return v

    @validator('timestamp')
    def timestamp_valid(cls, v: int) -> int:
        try:
            dt = datetime.fromtimestamp(v, timezone.utc)
            timestamp = int(dt.timestamp())
        except Exception:
            raise ValueError('not a valid timestamp')

        now = int((datetime.now() + timedelta(minutes=1)).timestamp())
        if timestamp > now:
            raise ValueError(f'observations from the future are not allowed. '
                             f'Observation timestamp: {timestamp}. Current timestamp: {now}')

        return timestamp
