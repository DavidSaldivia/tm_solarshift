import pandas as pd
import pytest

from tm_solarshift.general import Simulation
from tm_solarshift.constants import SIMULATIONS_IO
from tm_solarshift.utils.units import Variable

from tm_solarshift.models.dewh import DEWH
from tm_solarshift.models.resistive_single import ResistiveSingle
from tm_solarshift.models.heat_pump import HeatPump
from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary
from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)

@pytest.fixture(scope="module")
def sim_default():
    return Simulation()

# def test_create_ts_all(sim_default: Simulation):

#     ts = sim_default.create_ts()
#     expected_cols = SIMULATIONS_IO.TS_COLUMNS_ALL
#     expected_len = sim_default.thermal_sim.PERIODS.get_value()

#     assert type(ts) == pd.DataFrame
#     assert ts.columns.to_list() == expected_cols
#     assert len(ts) == expected_len

# @pytest.mark.parametrize("DEWH", [
#     ResistiveSingle, HeatPump, GasHeaterStorage, SolarThermalElecAuxiliary, 
# ])
# def test_run_thermal_simulation(DEWH: DEWH, sim_default: Simulation):
#     sim_default.thermal_sim.STOP = Variable(24, "hr")
#     expected_cols_sim = SIMULATIONS_IO.OUTPUT_SIM_DEWH
#     expected_cols_tm = SIMULATIONS_IO.OUTPUT_ANALYSIS_TM
#     expected_len = sim_default.thermal_sim.PERIODS.get_value()
#     (out_all, out_overall) = sim_default.run_thermal_simulation()
    
#     assert (set(expected_cols_sim).issubset(set(out_all.columns.to_list())))
#     assert (set(expected_cols_tm).issubset(set(out_overall.keys())))
#     assert (len(out_all) == expected_len)


def test_load_ts_all(sim_default: Simulation):
    ts = sim_default.load_ts(ts_types= list(SIMULATIONS_IO.TS_TYPES.keys()) )
    expected_cols = SIMULATIONS_IO.TS_COLUMNS_ALL
    expected_len = sim_default.thermal_sim.PERIODS.get_value()

    assert type(ts) == pd.DataFrame
    assert ts.columns.to_list() == expected_cols
    assert len(ts) == expected_len


@pytest.mark.parametrize("DEWH", [
    ResistiveSingle, HeatPump, GasHeaterStorage, SolarThermalElecAuxiliary, 
])
def test_run_simulation(DEWH: DEWH, sim_default: Simulation):
    sim_default.thermal_sim.STOP = Variable(24, "hr")
    expected_cols_sim = SIMULATIONS_IO.OUTPUT_SIM_DEWH
    expected_cols_tm = SIMULATIONS_IO.OUTPUT_ANALYSIS_TM
    expected_len = sim_default.thermal_sim.PERIODS.get_value()
    
    sim_default.run_simulation()

    df_tm = sim_default.out["df_tm"]
    overall_tm = sim_default.out["overall_tm"]
    
    assert (set(expected_cols_sim).issubset(set(df_tm.columns.to_list())))
    assert (set(expected_cols_tm).issubset(set(overall_tm.keys())))
    assert (len(df_tm) == expected_len)
