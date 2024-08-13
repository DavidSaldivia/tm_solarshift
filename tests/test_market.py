import pytest

from tm_solarshift.general import Simulation
from tm_solarshift.timeseries import market

#--------------------
@pytest.mark.parametrize("location, tariff_type", [
    ("Sydney", "flat"),
    ("Sydney", "CL"),
    ("Melbourne", "tou"),
    ("Brisbane", "flat"),
    ("Adelaide", "tou"),
])
def test_load_household_import_rate(location: str, tariff_type: str):
    sim = Simulation()
    sim.household.location = location
    sim.household.tariff_type = tariff_type
    ts_index = sim.time_params.idx
    ts_mkt = market.load_household_import_rate(
        ts_index,
        tariff_type = sim.household.tariff_type,
        dnsp = sim.household.DNSP,
        control_type= sim.household.control_type,
    )
    assert len(ts_mkt[ts_mkt["tariff"].isnull()]) == 0


def test_load_household_gas_rate():
    import pandas as pd
    sim = Simulation()
    ts_index = sim.time_params.idx
    ts_power_mock = pd.Series(0.01,index=ts_index)
    ts_mkt = market.load_household_gas_rate(ts_power_mock)
    assert len(ts_mkt[ts_mkt["tariff"].isnull()]) == 0


def test_load_emission_index():
    import pandas as pd
    sim = Simulation()
    ts_index = sim.time_params.idx
    STEP_h = sim.time_params.STEP.get_value("hr")
    TOTAL_HOURS = (sim.time_params.STOP.get_value("hr") - sim.time_params.START.get_value("hr"))
    
    avg_emissions = 0.65 #for NSW 2022
    power_mock = 0.01

    ts_mock = pd.DataFrame(power_mock,index=ts_index, columns=["heater_heat"]) #[MW]
    index_type = "total"
    ts_mkt = market.load_emission_index_year(
        timeseries=ts_mock,
        location="Sydney",
        index_type=index_type,
        year=2022,
    )
    expected_total = power_mock * TOTAL_HOURS * avg_emissions
    emissions_total = (ts_mock["heater_heat"] * STEP_h * ts_mkt["intensity_index"]).sum()
    assert emissions_total>0.
    assert abs(emissions_total - expected_total) < 1.0