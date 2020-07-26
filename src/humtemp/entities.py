from typing import *

from pydantic import BaseModel

from humtemp.dto.observation import LabId

BucketKey = NewType('BucketKey', str)


class BucketEntity(BaseModel):
    KEY_PREFIX: ClassVar[str] = 'bucket'

    key: BucketKey

    num_observations: int = 0
    sum_temp: float = 0.0
    sum_humidity: float = 0.0

    @property
    def avg_temp(self):
        if self.num_observations == 0:
            return 0
        else:
            return self.sum_temp / self.num_observations

    @property
    def avg_humidity(self):
        if self.num_observations == 0:
            return 0
        else:
            return self.sum_humidity / self.num_observations

    @property
    def lab_id(self) -> LabId:
        return BucketEntity.deconstruct_key(self.key)[0]

    @classmethod
    def construct_key(cls, lab_id: LabId, bucket_start: int) -> BucketKey:
        return BucketKey(f'{cls.KEY_PREFIX}:{lab_id}:{bucket_start}')

    @classmethod
    def deconstruct_key(cls, key: Union[str, bytes]) -> Tuple[LabId, int]:
        if isinstance(key, bytes):
            key = key.decode('ascii')

        type_, lab_id, timestamp = key.split(':')
        if type_ != cls.KEY_PREFIX:
            raise ValueError(f'the provided key {key} is not of the correct type')

        return LabId(lab_id), int(timestamp)
