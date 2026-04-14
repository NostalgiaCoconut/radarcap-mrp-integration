import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests, logging
from typing import List, Optional
from datetime import date, datetime, timezone
from connectors.base import (MRPConnector, WorkCenter, ProductionProgram,
    DemandForecast, CapacityRequirement, OEERecord)
from config.settings import SAPConfig

logger = logging.getLogger(__name__)


class SAPConnector(MRPConnector):
    """
    SAP S/4HANA Cloud connector — entity sets confirmed from sandbox diagnostic:
      Work Centers:   API_WORK_CENTERS / A_WorkCenterAllCapacity
      Products:       API_PRODUCT_SRV  / A_ProductPlant
      Maintenance:    API_MAINTNOTIFICATION / MaintenanceNotification
    """

    def __init__(self, config: SAPConfig):
        self.config  = config
        self.session = requests.Session()

    def authenticate(self) -> bool:
        if not self.config.api_key:
            logger.error("SAP_API_KEY not set in .env")
            return False
        self.session.headers.update({
            "APIKey": self.config.api_key,
            "Accept": "application/json",
        })
        # Use confirmed working entity from diagnostic
        try:
            url = f"{self.config.base_url}/API_WORK_CENTERS/A_WorkCenterAllCapacity"
            r   = self.session.get(url, params={"$top": "1", "$format": "json"}, timeout=self.config.timeout)
            logger.info(f"SAP auth status: {r.status_code}")
            if r.status_code == 200:
                logger.info("SAP connection OK")
                return True
            logger.error(f"SAP auth failed {r.status_code}: {r.text[:150]}")
            return False
        except Exception as e:
            logger.error(f"SAP connection error: {e}")
            return False

    def get_work_centers(self, plant=None) -> List[WorkCenter]:
        """
        Confirmed working: API_WORK_CENTERS / A_WorkCenterAllCapacity
        Also has: A_WorkCenterCapacity, A_WorkCenterCapacityInterval
        """
        plant  = plant or self.config.plant
        try:
            # Get work center headers
            results = self._get(
                f"{self.config.base_url}/API_WORK_CENTERS/A_WorkCenterAllCapacity",
                {"$top": "500", "$format": "json",
                 "$select": "WorkCenter,Plant,WorkCenterTypeCode,WorkCenterCategoryCode"}
            )
            # Filter by plant
            if plant:
                results = [r for r in results if r.get("Plant","") == plant]
            logger.info(f"Fetched {len(results)} work centers")
            seen = set()
            wcs  = []
            for r in results:
                wc_id = r.get("WorkCenter","")
                if wc_id and wc_id not in seen:
                    seen.add(wc_id)
                    wcs.append(WorkCenter(
                        id               = wc_id,
                        name             = r.get("WorkCenterDesc", wc_id),
                        plant            = r.get("Plant", plant),
                        capacity_hrs_mo  = 320.0,
                        availability_pct = 95.0,
                        shift_pattern    = "2 shift 9/80",
                        quantity         = 1,
                    ))
            return wcs
        except Exception as e:
            logger.error(f"get_work_centers: {e}"); return []

    def get_programs(self) -> List[ProductionProgram]:
        """Confirmed working: API_PRODUCT_SRV / A_ProductPlant"""
        try:
            results = self._get(
                f"{self.config.base_url}/API_PRODUCT_SRV/A_ProductPlant",
                {"$filter": f"Plant eq '{self.config.plant}'",
                 "$select": "Product,Plant,MRPType",
                 "$top": "200", "$format": "json"}
            )
            logger.info(f"Fetched {len(results)} programs")
            return [ProductionProgram(
                id=r.get("Product",""), name=r.get("Product",""),
                type="Commercial", priority=1, base_yield=85.0, cycle_time=1.0,
                sop=date.today(), eop=date(2030,12,31)
            ) for r in results]
        except Exception as e:
            logger.error(f"get_programs: {e}"); return []

    def get_demand_forecast(self, program_ids=None, start_date=None, end_date=None) -> List[DemandForecast]:
        """
        API_PLANNED_ORDERS_SRV returns 403 on sandbox.
        Using A_Product quantities as proxy demand data.
        """
        logger.warning("Planned orders not available in sandbox — using product master as proxy")
        try:
            results = self._get(
                f"{self.config.base_url}/API_PRODUCT_SRV/A_ProductPlant",
                {"$filter": f"Plant eq '{self.config.plant}'",
                 "$select": "Product,Plant",
                 "$top": "50", "$format": "json"}
            )
            today = date.today()
            forecasts = []
            for r in results:
                pid = r.get("Product","")
                if program_ids and pid not in program_ids:
                    continue
                # Generate 12 months of placeholder demand
                for m in range(1, 13):
                    forecasts.append(DemandForecast(
                        program_id=pid, year=today.year, month=m, quantity=10.0
                    ))
            logger.info(f"Generated {len(forecasts)} placeholder demand records")
            return forecasts
        except Exception as e:
            logger.error(f"get_demand_forecast: {e}"); return []

    def get_capacity_requirements(self, work_center_ids=None, start_date=None, end_date=None) -> List[CapacityRequirement]:
        """
        API_PRODUCTION_ORDERS_SRV returns 403 on sandbox.
        Using WorkCenter capacity intervals as proxy.
        """
        logger.warning("Production orders not available in sandbox — using capacity intervals as proxy")
        try:
            results = self._get(
                f"{self.config.base_url}/API_WORK_CENTERS/A_WorkCenterCapacityInterval",
                {"$top": "200", "$format": "json",
                 "$select": "WorkCenter,Plant,CapacityRequirement"}
            )
            if self.config.plant:
                results = [r for r in results if r.get("Plant","") == self.config.plant]
            reqs = []
            today = date.today()
            for r in results:
                wc = r.get("WorkCenter","")
                if work_center_ids and wc not in work_center_ids:
                    continue
                reqs.append(CapacityRequirement(
                    work_center_id=wc, program_id="SANDBOX",
                    year=today.year, month=today.month,
                    hours_required=float(r.get("CapacityRequirement", 8.0))
                ))
            logger.info(f"Fetched {len(reqs)} capacity records")
            return reqs
        except Exception as e:
            logger.error(f"get_capacity_requirements: {e}"); return []

    def get_oee_data(self, equipment_ids=None, start_date=None, end_date=None) -> List[OEERecord]:
        """Confirmed working: API_MAINTNOTIFICATION / MaintenanceNotification"""
        try:
            results = self._get(
                f"{self.config.base_url}/API_MAINTNOTIFICATION/MaintenanceNotification",
                {"$top": "200", "$format": "json",
                 "$select": "MaintenanceNotification,Equipment,MaintNotifCreationDate,MaintNotifType"}
            )
            logger.info(f"Fetched {len(results)} maintenance notifications")
            records = []
            for r in results:
                eq = r.get("Equipment","")
                if equipment_ids and eq not in equipment_ids:
                    continue
                dt = self._parse_date(r.get("MaintNotifCreationDate",""))
                if dt:
                    records.append(OEERecord(
                        equipment_id=eq or r.get("MaintenanceNotification",""),
                        year=dt.year, month=dt.month,
                        availability=95.0, performance=87.0, quality=98.0,
                        oee=round(0.95*0.87*0.98, 4),
                        downtime_hrs=0.0
                    ))
            return records
        except Exception as e:
            logger.error(f"get_oee_data: {e}"); return []

    def push_capacity_plan(self, plan):
        logger.warning("API Hub sandbox is read-only"); return False

    def _get(self, url, params):
        r = self.session.get(url, params=params, timeout=self.config.timeout)
        r.raise_for_status()
        return r.json().get("d", {}).get("results", [])

    @staticmethod
    def _parse_date(s):
        if not s: return None
        if s.startswith("/Date("):
            return datetime.fromtimestamp(int(s[6:-2].split("+")[0])/1000, tz=timezone.utc).replace(tzinfo=None)
        try: return datetime.fromisoformat(s[:10])
        except: return None
