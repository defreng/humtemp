from pydantic import BaseModel

from humtemp.dto.observation import LabId


class Summary(BaseModel):
    lab_id: LabId
    avg_temp: float
    avg_humidity: float
