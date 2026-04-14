from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from datetime import date


@dataclass
class WorkCenter:
    id:               str
    name:             str
    plant:            str
    capacity_hrs_mo:  float
    availability_pct: float
    shift_pattern:    str
    quantity:         int = 1


@dataclass
class ProductionProgram:
    id:          str
    name:        str
    type:        str
    priority:    int
    base_yield:  float
    cycle_time:  float
    sop:         date
    eop:         date
    status:      str = "Active"


@dataclass
class DemandForecast:
    program_id: str
    year:       int
    month:      int
    quantity:   float


@dataclass
class CapacityRequirement:
    work_center_id: str
    program_id:     str
    year:           int
    month:          int
    hours_required: float


@dataclass
class OEERecord:
    equipment_id:  str
    year:          int
    month:         int
    availability:  float
    performance:   float
    quality:       float
    oee:           float
    downtime_hrs:  float


class MRPConnector(ABC):

    @abstractmethod
    def authenticate(self) -> bool: ...

    @abstractmethod
    def get_work_centers(self, plant: Optional[str] = None) -> List[WorkCenter]: ...

    @abstractmethod
    def get_programs(self) -> List[ProductionProgram]: ...

    @abstractmethod
    def get_demand_forecast(self, program_ids=None, start_date=None, end_date=None) -> List[DemandForecast]: ...

    @abstractmethod
    def get_capacity_requirements(self, work_center_ids=None, start_date=None, end_date=None) -> List[CapacityRequirement]: ...

    @abstractmethod
    def get_oee_data(self, equipment_ids=None, start_date=None, end_date=None) -> List[OEERecord]: ...

    @abstractmethod
    def push_capacity_plan(self, plan: List[CapacityRequirement]) -> bool: ...

    def health_check(self) -> dict:
        try:
            ok = self.authenticate()
            return {"status": "ok" if ok else "auth_failed", "system": self.__class__.__name__}
        except Exception as e:
            return {"status": "error", "system": self.__class__.__name__, "detail": str(e)}
