from copy import deepcopy
import pandas as pd
import pytest

from tm_solarshift.general import Simulation
from tm_solarshift.constants import SIMULATIONS_IO
from tm_solarshift.utils.units import Variable

@pytest.fixture(scope="module")
def sim_default():
    return Simulation()


def test_load_ts_all(sim_default: Simulation):
    sim = deepcopy(sim_default)
    ts = sim.load_ts(ts_types= list(SIMULATIONS_IO.TS_TYPES.keys()) )
    expected_cols = SIMULATIONS_IO.TS_COLUMNS_ALL
    expected_len = sim.time_params.PERIODS.get_value()

    assert type(ts) == pd.DataFrame
    assert ts.columns.to_list() == expected_cols
    assert len(ts) == expected_len


def test_control_signal_loading(sim_default: Simulation):
    sim = deepcopy(sim_default)
    ts_control = sim.load_ts(ts_types=["control"])
    expected_len_ts = sim.time_params.PERIODS.get_value()
    expected_cols_ts = SIMULATIONS_IO.TS_TYPES["control"]
    assert len(ts_control) == expected_len_ts
    assert (set(expected_cols_ts).issubset(set( ts_control.columns.to_list())))


@pytest.mark.parametrize("control_type", [
    "GS", "CL1", "CL2", "CL3", "timer", "diverter"
])
def test_run_simulation_control(control_type: str, sim_default: Simulation):
    sim = deepcopy(sim_default)
    sim.time_params.STOP = Variable(24, "hr")
    sim.household.control_type = control_type
    expected_cols_sim = SIMULATIONS_IO.OUTPUT_SIM_DEWH
    expected_keys_tm = SIMULATIONS_IO.OUTPUT_ANALYSIS_TM
    expected_len = sim.time_params.PERIODS.get_value()
    
    sim.run_simulation()

    df_tm = sim.out["df_tm"]
    overall_tm = sim.out["overall_tm"]
    
    assert (len(df_tm) == expected_len)
    assert (set(expected_cols_sim).issubset(set(df_tm.columns.to_list())))
    assert (set(expected_keys_tm).issubset(set(overall_tm.keys())))
