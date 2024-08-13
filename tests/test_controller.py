from copy import deepcopy
import numpy as np
import pandas as pd
import pytest

from tm_solarshift.constants import SIMULATIONS_IO
from tm_solarshift.general import Simulation
from tm_solarshift.models.control import (CLController, Timer, add_random_delay)


@pytest.mark.parametrize("controller_type, time_avg", [
    ("GS", 24.0),
    ("CL1", 9.05),
    ("CL2", 20.22),
    ("CL3", 14.54),
])
def test_CL_no_random(controller_type: str, time_avg: float):
    
    random_delay = False
    sim = Simulation()
    ts_index = sim.create_ts_index()
    STEP_h = sim.time_params.STEP.get_value("hr")

    controller = CLController( CL_type=controller_type, random_delay=random_delay )
    ts_control = controller.create_signal(ts_index)

    time_per_day_avg = ts_control.groupby(ts_control.index.date)["CS"].sum().mean() * STEP_h
    expected_time_per_day_avg = time_avg

    expected_len_ts = sim.time_params.PERIODS.get_value()
    expected_cols_ts = SIMULATIONS_IO.TS_TYPES["control"]
    
    assert len(ts_control) == expected_len_ts
    assert (set(expected_cols_ts).issubset(set( ts_control.columns.to_list())))
    assert abs(time_per_day_avg - expected_time_per_day_avg) < 0.5



@pytest.mark.parametrize("controller_type, time_avg", [
    ("timer_SS", 6.0),
    ("timer_OP", 9.05),
])
def test_timer_SS_OP(controller_type: str, time_avg: float):
    random_delay = False
    sim = Simulation()
    ts_index = sim.create_ts_index()
    STEP_h = sim.time_params.STEP.get_value("hr")

    controller = Timer(timer_type = controller_type, random_delay=random_delay)
    ts_control = controller.create_signal(ts_index)

    ts_index = pd.to_datetime(ts_control.index)
    time_per_day_avg = ts_control.groupby(ts_index.date)["CS"].sum().mean() * STEP_h
    time_per_day_std = ts_control.groupby(ts_index.date)["CS"].sum().std() * STEP_h

    expected_time_per_day_avg = time_avg
    expected_time_per_day_std = 0.0

    expected_len_ts = sim.time_params.PERIODS.get_value()
    expected_cols_ts = SIMULATIONS_IO.TS_TYPES["control"]
    
    assert len(ts_control) == expected_len_ts
    assert (set(expected_cols_ts).issubset(set( ts_control.columns.to_list())))
    assert abs(time_per_day_avg - expected_time_per_day_avg) < 0.5



def test_timer_custom():
    random_delay = False
    sim = Simulation()
    ts_index = sim.create_ts_index()
    STEP_h = sim.time_params.STEP.get_value("hr")

    controller = Timer(
        timer_type = "timer",
        random_delay = random_delay,
        time_start = 0.0,
        time_stop = 4.0,
        )
    ts_control = controller.create_signal(ts_index)

    ts_index = pd.to_datetime(ts_control.index)
    time_per_day_avg = ts_control.groupby(ts_index.date)["CS"].sum().mean() * STEP_h
    time_per_day_std = ts_control.groupby(ts_index.date)["CS"].sum().std() * STEP_h

    expected_time_per_day_avg = 4.0
    expected_time_per_day_std = 0.0

    expected_len_ts = sim.time_params.PERIODS.get_value()
    expected_cols_ts = SIMULATIONS_IO.TS_TYPES["control"]
    
    assert len(ts_control) == expected_len_ts
    assert (set(expected_cols_ts).issubset(set( ts_control.columns.to_list())))
    assert abs(time_per_day_avg - expected_time_per_day_avg) < 0.5



def test_randomization_delay():
    #creating a series without delay
    random_delay = False
    sim = Simulation()
    ts_index = sim.create_ts_index()
    STEP_h = sim.time_params.STEP.get_value("hr")
    controller = CLController( CL_type="CL1", random_delay=random_delay )
    cs_no_random = np.array(controller.create_signal(ts_index)["CS"])

    cs_final = add_random_delay(
        cs_no_random,
        random_delay_on = 60,
        random_delay_off = 30,
    )
    assert isinstance(cs_final, np.ndarray)
    assert not(np.isnan(np.sum(cs_final)))


@pytest.mark.parametrize("controller_type, time_avg", [
    ("GS", 24.0),
    ("CL1", 7.5),
    ("CL2", 18.7),
    ("CL3", 11.5),
])
def test_CL_random(controller_type: str, time_avg: float):
    
    random_delay = True
    sim = Simulation()
    ts_index = sim.create_ts_index()
    STEP_h = sim.time_params.STEP.get_value("hr")

    controller = CLController( CL_type=controller_type, random_delay=random_delay )
    ts_control = controller.create_signal(ts_index)

    time_per_day_avg = ts_control.groupby(ts_control.index.date)["CS"].sum().mean() * STEP_h
    # time_per_day_std = ts_control.groupby(ts_control.index.date)["CS"].sum().std() * STEP_h
    expected_time_per_day_avg = time_avg

    expected_len_ts = sim.time_params.PERIODS.get_value()
    expected_cols_ts = SIMULATIONS_IO.TS_TYPES["control"]
    
    assert len(ts_control) == expected_len_ts
    assert (set(expected_cols_ts).issubset(set( ts_control.columns.to_list())))
    assert abs(time_per_day_avg - expected_time_per_day_avg) < 0.5