from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class MRPSystem(Enum):
    SAP      = "sap"
    ORACLE   = "oracle"
    DYNAMICS = "dynamics"


@dataclass
class SAPConfig:
    base_url:       str
    api_key:        str  = ""
    token_url:      str  = ""
    client_id:      str  = ""
    client_secret:  str  = ""
    client:         str  = "100"
    username:       str  = ""
    password:       str  = ""
    plant:          str  = "1710"
    timeout:        int  = 30
    work_center_service:      str = "API_WORK_CENTERS"
    demand_service:           str = "API_PLANNED_ORDERS_SRV"
    production_order_service: str = "API_PRODUCTION_ORDERS_SRV"
    oee_service:              str = "API_MAINTNOTIFICATION"
    capacity_service:         str = "PP_CAPACITY_PLANNING_SRV"

    @property
    def use_api_key(self) -> bool:
        return bool(self.api_key)

    @property
    def use_btp_oauth(self) -> bool:
        return bool(self.token_url and self.client_id and self.client_secret)


@dataclass
class OracleConfig:
    base_url:        str
    username:        str
    password:        str
    organization_id: str
    timeout:         int = 30


@dataclass
class DynamicsConfig:
    tenant_id:       str
    client_id:       str
    client_secret:   str
    environment_url: str
    timeout:         int = 30


@dataclass
class RadarCapConfig:
    import_folder:         str = "./radarcap_imports"
    export_folder:         str = "./radarcap_exports"
    template_folder:       str = "./templates"
    sync_interval_minutes: int = 60
    active_mrp: MRPSystem      = MRPSystem.SAP


@dataclass
class IntegrationConfig:
    radarcap: RadarCapConfig           = field(default_factory=RadarCapConfig)
    sap:      Optional[SAPConfig]      = None
    oracle:   Optional[OracleConfig]   = None
    dynamics: Optional[DynamicsConfig] = None
