import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date
from unittest.mock import patch
from connectors.base import WorkCenter, ProductionProgram, DemandForecast, CapacityRequirement, OEERecord
from connectors.sap_connector import SAPConnector
from mappers.radarcap_mapper import RadarCapMapper, _month_cols
from config.settings import SAPConfig


@pytest.fixture
def cfg():
    return SAPConfig(base_url="https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap", api_key="test-key", plant="1710")

@pytest.fixture
def wcs():
    return [WorkCenter("WC-001","Fuselage Assembly","1710",320,96.5,"2 shift 9/80",6),
            WorkCenter("WC-002","Wing Assembly Jig","1710",312,97.2,"2 shift 4 10s",4)]

@pytest.fixture
def progs():
    return [ProductionProgram("MAT-001","Falcon-X7","Commercial",1,82.0,0.85,date(2026,1,1),date(2030,12,31)),
            ProductionProgram("MAT-002","Eagle-450","Military",2,78.0,0.95,date(2026,1,1),date(2030,12,31)),
            ProductionProgram("MAT-003","JetStream-100","Commercial",2,90.0,0.42,date(2026,1,1),date(2030,12,31))]

@pytest.fixture
def forecasts():
    return [DemandForecast("MAT-001",2026,1,6.3), DemandForecast("MAT-002",2026,1,4.6)]

@pytest.fixture
def reqs():
    return [CapacityRequirement("WC-001","MAT-001",2026,1,6.7), CapacityRequirement("WC-001","MAT-002",2026,1,11.0)]

@pytest.fixture
def oee():
    return [OEERecord("WC-001",2026,1,96.5,87.3,96.8,0.815,51.2)]


class TestSAPConnector:
    def test_auth_no_key(self):
        c = SAPConnector(SAPConfig(base_url="https://test.com"))
        assert c.authenticate() is False

    def test_health_check_ok(self, cfg):
        c = SAPConnector(cfg)
        with patch.object(c, 'authenticate', return_value=True):
            assert c.health_check()["status"] == "ok"

    def test_parse_date_v2(self):
        dt = SAPConnector._parse_date("/Date(1735689600000)/")
        assert dt is not None and dt.year == 2025

    def test_parse_date_iso(self):
        dt = SAPConnector._parse_date("2026-03-15")
        assert dt is not None and dt.month == 3

    def test_parse_date_empty(self):
        assert SAPConnector._parse_date("") is None


class TestMapper:
    def test_equipment_master(self, wcs):
        df = RadarCapMapper.to_equipment_master(wcs)
        assert len(df) == 2
        assert list(df["Equipment_ID"]) == ["EQ-001","EQ-002"]

    def test_programs_master(self, progs):
        df = RadarCapMapper.to_programs_master(progs)
        assert len(df) == 3

    def test_demand_forecast(self, forecasts, progs):
        df = RadarCapMapper.to_demand_forecast(forecasts, progs, 2026, 2026)
        assert "Jan-2026" in df.columns
        row = df[df["Program"] == "Falcon-X7"]
        assert not row.empty and row["Jan-2026"].values[0] == 6.3

    def test_capacity_sheet(self, reqs, progs):
        df = RadarCapMapper.to_capacity_sheet(reqs,"WC-001","Fuselage",progs,2026,2026)
        assert len(df) == 2

    def test_month_cols(self):
        cols = _month_cols(2026, 2030)
        assert len(cols) == 60 and cols[0] == "Jan-2026"

    def test_oee_status(self, oee):
        df = RadarCapMapper.to_oee_tracking(oee, {"WC-001":"Fuselage Assembly"})
        assert df["OEE_Status"].iloc[0] in ["World-Class","Good","Average"]
