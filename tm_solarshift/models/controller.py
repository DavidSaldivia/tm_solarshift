import json
import os
import numpy as np
import pandas as pd
from typing import Protocol, TypedDict

from tm_solarshift.constants import SIMULATIONS_IO
from tm_solarshift.timeseries import control

from tm_solarshift.constants import (
    DEFINITIONS,
    DIRECTORY,
    SIMULATIONS_IO
)


# TS_TYPES = SIMULATIONS_IO.TS_TYPES
# COLS_CONTROL = TS_TYPES["control"]
# CONTROL_TYPES = DEFINITIONS.CONTROL_TYPES
DIR_CONTROL = DIRECTORY.DIR_DATA["control"]

class Period(TypedDict):
    label: str                     # only used as reference
    month_start: int               # inclusive
    month_stop: int                # inclusive
    time_start: float              # inclusive
    time_stop: float               # inclusive
    random_on: float               # [mins]
    random_off: float              # [mins]


class Controller(Protocol):
    def create_signal(
            self,
            ts_index: pd.DatetimeIndex | None,
            ts: pd.DataFrame | None
        ) -> pd.DataFrame:
        ...


class CLController():
    def __init__(self, control_load: int = 0, random_on: bool = False):
        self.type = "CL"
        self.control_load = control_load
        self.random_on = random_on


    def create_signal(
            self,
            ts_index: pd.DatetimeIndex
    ) -> pd.DataFrame:
        
        control_load = self.control_load
        random_on = self.random_on
        STEP = ts_index.freq.n
        ts_control = pd.DataFrame(index=ts_index, columns=["CS"])
        
        periods = control.period_definitions(control_load)
        
        # Overwritting randomization to avoid error in function
        if control_load in [-1,0,10]:
            random_on = False
        
        (_, ts_control["CS"]) = control.create_signal_series(
            ts_control, periods, random_ON=random_on, STEP=STEP
        )
        return ts_control
    
    

#--------------------------
def load_control_signal(
        idx: pd.DatetimeIndex,
        control_type: str = "GS",
        random_on: bool = True,
        random_seed: int = -1,
        timer_start: float = 0.,
        timer_length: float = 4.,
        cols: list[str] = SIMULATIONS_IO.TS_TYPES["control"],
) -> pd.DataFrame:

    # retrieving
    STEP = idx.freq.n

    # getting data
    match control_type:
        case "GS" | "CL1" | "CL2" | "CL3" | "timer_SS" | "timer_OP":
            periods = periods_from_json(control_type=control_type)

        case "diverter" | "timer":
            periods = [ period_custom(
                            time_start=timer_start,
                            time_stop = timer_start + timer_length
                        ), ]
        case _:
            raise ValueError(f"{control_type=} not among the valid options: {DEFINITIONS.CONTROL_TYPES=}")

    cs_no_rand = convert_periods_to_series(idx, periods)
    if random_on:
        cs_final = add_random_delay(cs_no_rand, random_seed, STEP=STEP)
    else:
        cs_final = cs_no_rand.to_frame().copy()

    df_control = pd.DataFrame(cs_final, index=idx, columns=cols)
    return df_control


def period_custom(
    label: str = "annual",
    month_start: int = 1,
    month_stop: int = 12,
    time_start: float = 0.0,
    time_stop: float = 3.0,
    random_on: float = 0.,
    random_off: float = 0.,
) -> Period:
    period: Period = {
            "label": label,  # only used as reference
            "month_start": month_start,  # inclusive
            "month_stop": month_stop,  # inclusive
            "time_start": time_start,  # inclusive
            "time_stop": time_stop,  # inclusive
            "random_on": random_on,  # [mins]
            "random_off": random_off,  # [mins]

    }
    return period


def periods_from_json(
        control_type: str = "GS",
) -> list[Period]:
    
    file_schedule = os.path.join(DIR_CONTROL, f'{control_type}.json')
    with open(file_schedule, 'r') as file:
        control_type_data = json.load(file)
    periods = control_type_data["schedule"]
    return periods


def convert_periods_to_series(
        idx: pd.DatetimeIndex,
        # periods: list[dict[str,int|float]],
        periods: list[Period],
) -> pd.Series:

    #TODO check if the .to_list() is working
    month = idx.month.astype(float)
    hour = (idx.hour + idx.minute / 60.0).astype(float)

    cs_periods = pd.Series(None, index=idx)

    for period in periods:
        # There are four cases:
        # 1.   (start_month <= stop_month) & (start_time <= stop_time)
        # 2.   (start_month >  stop_month) & (start_time <= stop_time)
        # 3.   (start_month <= stop_month) & (start_time >  stop_time)
        # 4.   (start_month >  stop_month) & (start_time >  stop_time)
        cases = [
            (
                (period["month_start"] <= period["month_stop"]) 
                and (period["time_start"] <= period["time_stop"])
            ),
            (
                (period["month_start"] > period["month_stop"])
                and (period["time_start"] <= period["time_stop"])
            ),
            (
                (period["month_start"] <= period["month_stop"])
                and (period["time_start"] > period["time_stop"])
            ),
            (
                (period["month_start"] > period["month_stop"])
                and (period["time_start"] > period["time_stop"])
            )
        ]
        # With four conditions:
        conditions = [
            (
                ((month >= period["month_start"]) & (month <= period["month_stop"]))
                & ((hour >= period["time_start"]) & (hour <= period["time_stop"]))
            ),
            (
                ((month >= period["month_start"]) | (month <= period["month_stop"]))
                & ((hour >= period["time_start"]) & (hour <= period["time_stop"]))
            ),
            (
                ((month >= period["month_start"]) & (month <= period["month_stop"]))
                & ((hour >= period["time_start"]) | (hour <= period["time_stop"]))
            ),
            (
                ((month >= period["month_start"]) | (month <= period["month_stop"]))
                & ((hour >= period["time_start"]) | (hour <= period["time_stop"]))
            )
        ]
        
        #Applying conditions and adding it to the control signal
        cs_aux = None
        for (i,case) in enumerate(cases):
            if case:
                cs_aux = np.where(conditions[i], 1, 0)
        
        cs_periods = pd.Series(
            np.where(((cs_periods == 1) | (cs_aux == 1)), 1, 0)
            , index=idx
        )
    return cs_periods


#--------------------
def add_random_delay(
    cs_periods: pd.Series,
    random_delay_on: int = 0,
    random_delay_off: int = 0,
    STEP: int = 3,
    seed_id: int = -1,
) -> pd.DataFrame:

    # TODO replace this one
    if seed_id == -1:
        seed = np.random.SeedSequence().entropy
    else:
        seed = seed_id
    
    rng = np.random.default_rng(seed)
    df_initial = pd.DataFrame(cs_periods, columns=["CS"])
    df_initial["switch_no_rand"] = df_initial["CS"].diff()  # Values 1=ON, -1=OFF

    # TODO can we use a for loop here? over 1 (starting_times) and -1 (stopping_times)
    # getting starting and stoping times without randomisation
    df_starting_times = df_initial[df_initial["switch_no_rand"] == 1].copy()
    df_starting_times["time_no_rand"] = df_starting_times.index
    df_stopping_times = df_initial[df_initial["switch_no_rand"] == -1].copy()
    df_stopping_times["time_no_rand"] = df_stopping_times.index

    # creating randomization delays for on and off
    df_starting_times["delays_on"] = rng.choice(
        np.arange(0, random_delay_on + 1, STEP), size=len(df_starting_times),
    )
    df_stopping_times["delays_off"] = rng.choice(
        np.arange(0, random_delay_off + 1, STEP), size=len(df_stopping_times)
    )

    #last delays are = 0 to avoid get outside indexes
    # TODO Is this step needed?
    df_starting_times.iloc[-1, df_starting_times.columns.get_loc("delays_on")] = 0
    df_stopping_times.iloc[-1, df_stopping_times.columns.get_loc("delays_off")] = 0

    # Defining starting and stopping times once randomization is applied
    df_starting_times["time_with_rand"] = df_starting_times.apply(
        lambda aux: aux["time_no_rand"] + pd.offsets.Minute(aux["delays_on"]), axis=1
    )
    df_stopping_times["time_with_rand"] = df_stopping_times.apply(
        lambda aux: aux["time_no_rand"]  + pd.offsets.Minute(aux["delays_off"]), axis=1,
    )
    # Applying the randomization into the final dataframe
    df_final = df_initial.copy()
    df_final["time_rand"] = 0         # TODO is this needed?
    df_final.loc[df_starting_times["time_with_rand"], "time_rand"] = 1
    df_final.loc[df_stopping_times["time_with_rand"], "time_rand"] = -1
    output = (df_final.iloc[0]["CS"] + df_final["time_rand"].cumsum())  # TODO check this part
    return output




class Timer():
    def __init__(self):
        self.type = "timer"
        self.time_start = 0
        self.time_stop = 3
        self.random_on = False


    def create_signal(self, ts_index: pd.DatetimeIndex) -> pd.DataFrame:
        return pd.DataFrame()
    

class Diverter():
    def __init__(self):
        self.type = "diverter"
        self.time_start = 0
        self.time_stop = 3


    def create_signal(self, ts: pd.DataFrame) -> pd.DataFrame:

        if "pv_power" in ts.columns:
            pv_power = ts["pv_power"]
        else:
            pv_power = pd.Series(0, index=ts.index, name="pv_power")
        
        return pd.DataFrame()