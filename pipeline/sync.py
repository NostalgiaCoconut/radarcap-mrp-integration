import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json, logging
from datetime import date, datetime
from pathlib import Path
import pandas as pd
from config.settings import IntegrationConfig, MRPSystem, SAPConfig, RadarCapConfig
from connectors.sap_connector import SAPConnector
from mappers.radarcap_mapper import RadarCapMapper

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class SyncPipeline:
    def __init__(self, config):
        self.config    = config
        self.mapper    = RadarCapMapper()
        self.connector = SAPConnector(config.sap)

    def health_check(self):
        return self.connector.health_check()

    def run_full_sync(self, start_date=None, end_date=None):
        start_date = start_date or date(2026, 1, 1)
        end_date   = end_date   or date(2030, 12, 31)
        summary    = {"status": "ok", "records": {}}

        if not self.connector.authenticate():
            summary["status"] = "auth_failed"
            return summary

        logger.info("Fetching from SAP...")
        wcs   = self.connector.get_work_centers()
        progs = self.connector.get_programs()
        fcast = self.connector.get_demand_forecast(start_date=start_date, end_date=end_date)
        reqs  = self.connector.get_capacity_requirements(start_date=start_date, end_date=end_date)
        oee   = self.connector.get_oee_data(start_date=start_date, end_date=end_date)

        summary["records"] = {
            "work_centers": len(wcs), "programs": len(progs),
            "demand_forecasts": len(fcast), "capacity_requirements": len(reqs),
            "oee_records": len(oee),
        }

        out = self._write_excel(wcs, progs, fcast, reqs, oee)
        summary["output_file"] = str(out)
        logger.info(f"Written: {out}")
        return summary

    def _write_excel(self, wcs, progs, fcast, reqs, oee):
        folder = Path(self.config.radarcap.import_folder)
        folder.mkdir(parents=True, exist_ok=True)

        # Use timestamp in filename — never conflicts with open files
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = folder / f"radarcap_import_{ts}.xlsx"

        # Remove files older than 48 hours to keep folder clean
        for old in folder.glob("radarcap_import_*.xlsx"):
            try:
                age_hrs = (datetime.now().timestamp() - old.stat().st_mtime) / 3600
                if age_hrs > 48:
                    old.unlink()
            except Exception:
                pass

        with pd.ExcelWriter(str(out), engine="openpyxl") as w:
            self.mapper.to_equipment_master(wcs).to_excel(w, sheet_name="Equipment_Master", index=False)
            self.mapper.to_programs_master(progs).to_excel(w, sheet_name="Programs_Master", index=False)
            self.mapper.to_demand_forecast(fcast, progs).to_excel(w, sheet_name="Demand_Forecast", index=False)
            self.mapper.to_oee_tracking(oee, {wc.id: wc.name for wc in wcs}).to_excel(w, sheet_name="OEE_Tracking", index=False)
            for wc in wcs[:20]:  # cap at 20 sheets to avoid Excel limits
                self.mapper.to_capacity_sheet(reqs, wc.id, wc.name, progs).to_excel(
                    w, sheet_name=wc.name[:31], index=False)
        return out


def _load_env():
    env = Path(__file__).parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


if __name__ == "__main__":
    _load_env()
    config = IntegrationConfig(
        radarcap=RadarCapConfig(active_mrp=MRPSystem.SAP),
        sap=SAPConfig(
            base_url=os.environ.get("SAP_BASE_URL","https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap"),
            api_key=os.environ.get("SAP_API_KEY",""),
            plant=os.environ.get("SAP_PLANT","1710"),
        ),
    )
    pipeline = SyncPipeline(config)
    print("Health:", pipeline.health_check())
    result = pipeline.run_full_sync()
    print(json.dumps(result, indent=2, default=str))
