import requests
import logging
from typing import List, Optional
from requests.auth import HTTPBasicAuth
from .base import MRPConnector, WorkCenter, ProductionProgram, DemandForecast, CapacityRequirement, OEERecord
from ..config.settings import OracleConfig

logger = logging.getLogger(__name__)


class OracleConnector(MRPConnector):
    """Oracle Fusion Cloud SCM — Phase 2."""

    def __init__(self, config: OracleConfig):
        self.config  = config
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(config.username, config.password)

    def authenticate(self) -> bool:
        try:
            resp = self.session.get(
                f"{self.config.base_url}/supplyChain/v1/itemWorkDefinitions",
                params={"limit": 1}, timeout=self.config.timeout,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Oracle auth failed: {e}")
            return False

    def get_work_centers(self, plant=None): raise NotImplementedError("Phase 2")
    def get_programs(self): raise NotImplementedError("Phase 2")
    def get_demand_forecast(self, **kw): raise NotImplementedError("Phase 2")
    def get_capacity_requirements(self, **kw): raise NotImplementedError("Phase 2")
    def get_oee_data(self, **kw): raise NotImplementedError("Phase 2")
    def push_capacity_plan(self, plan): raise NotImplementedError("Phase 2")
