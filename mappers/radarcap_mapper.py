import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import logging
from typing import List, Dict
from datetime import date
from calendar import month_abbr
from connectors.base import WorkCenter, ProductionProgram, DemandForecast, CapacityRequirement, OEERecord

logger = logging.getLogger(__name__)

def _month_cols(start_year=2026, end_year=2030):
    return [f"{month_abbr[m]}-{y}" for y in range(start_year, end_year+1) for m in range(1, 13)]

class RadarCapMapper:
    @staticmethod
    def to_equipment_master(wcs):
        rows = []
        for i, wc in enumerate(wcs, 1):
            mc = round((wc.capacity_hrs_mo * wc.availability_pct / 100) * wc.quantity)
            rows.append({"Equipment_ID": f"EQ-{i:03d}", "Equipment_Type": wc.name, "Quantity": wc.quantity,
                         "Assigned_Shift": wc.shift_pattern, "Shift_Hrs/Mo": wc.capacity_hrs_mo,
                         "Hrs/Wk": round(wc.capacity_hrs_mo/4.16,1), "Cycle_Time_Hrs": 1.0,
                         "Availability_%": wc.availability_pct, "Utilization_Target_%": 85,
                         "100%_MaxEquipCap": mc, "80%_MaxOpCap": round(mc*0.8)})
        return pd.DataFrame(rows)

    @staticmethod
    def to_programs_master(progs):
        rows = []
        for i, p in enumerate(progs, 1):
            rows.append({"Program_ID": f"PRG-{i:03d}", "Program_Name": p.name, "Type": p.type,
                         "Priority": p.priority, "Base_Yield_%": p.base_yield, "Monthly_Base_Demand": 0,
                         "Cycle_Time_Hrs": p.cycle_time, "SOP": p.sop.strftime("%b-%Y"),
                         "EOP": p.eop.strftime("%b-%Y"), "Status": p.status})
        return pd.DataFrame(rows)

    @staticmethod
    def to_demand_forecast(forecasts, programs, start_year=2026, end_year=2030):
        cols = _month_cols(start_year, end_year)
        pmap = {p.id: p.name for p in programs}
        data = {}
        for f in forecasts:
            n = pmap.get(f.program_id, f.program_id)
            if n not in data: data[n] = {c: 0.0 for c in cols}
            k = f"{month_abbr[f.month]}-{f.year}"
            if k in data[n]: data[n][k] += f.quantity
        return pd.DataFrame([{"Program": n, **m} for n, m in data.items()], columns=["Program"]+cols)

    @staticmethod
    def to_capacity_sheet(requirements, wc_id, wc_name, programs, start_year=2026, end_year=2030):
        cols = _month_cols(start_year, end_year)
        pmap = {p.id: p.name for p in programs}
        data = {}
        for r in [x for x in requirements if x.work_center_id == wc_id]:
            n = pmap.get(r.program_id, r.program_id)
            if n not in data: data[n] = {c: 0.0 for c in cols}
            k = f"{month_abbr[r.month]}-{r.year}"
            if k in data[n]: data[n][k] += r.hours_required
        return pd.DataFrame([{"Program": n, **m} for n, m in data.items()], columns=["Program"]+cols)

    @staticmethod
    def to_oee_tracking(oee_records, equipment_map):
        rows = []
        for r in oee_records:
            oee = round(r.oee*100,2) if r.oee<=1 else round(r.oee,2)
            rows.append({"Equipment_ID": r.equipment_id, "Equipment_Type": equipment_map.get(r.equipment_id, r.equipment_id),
                         "Month": f"{month_abbr[r.month]}-{r.year}", "Data_Type": "HISTORICAL",
                         "Availability_%": r.availability, "Performance_%": r.performance, "Quality_%": r.quality,
                         "OEE_%": oee, "OEE_Status": "World-Class" if oee>=85 else "Good" if oee>=65 else "Average",
                         "Downtime_Hrs": r.downtime_hrs})
        return pd.DataFrame(rows)
