import re
from datetime import datetime, timezone
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

        if dt > datetime.now(tz=timezone.utc):
            raise ValueError('observations from the future are not allowed')

        return timestamp
