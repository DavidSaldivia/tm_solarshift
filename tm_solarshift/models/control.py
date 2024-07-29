from dataclasses import dataclass
import json
import os
import numpy as np
import pandas as pd
from typing import Protocol, TypedDict

from tm_solarshift.timeseries.control import add_randomization_delay
from tm_solarshift.constants import (
    DEFINITIONS,
    DIRECTORY,
    SIMULATIONS_IO
)

DIR_CONTROL = DIRECTORY.DIR_DATA["control"]
CL_TYPES = ["GS", "CL1", "CL2", "CL3"]


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
        ) -> pd.DataFrame:
        ...


class CLController():
    def __init__(
            self,
            CL_type: str = "CL1",
            random_delay: bool = False,
            random_seed: int = -1
            ):
        if CL_type not in CL_TYPES:
            raise ValueError(f"not a valid CL_type. Allowed values: {CL_TYPES}.")
        
        self.CL_type = CL_type
        self.random_delay = random_delay
        self.random_seed: int = random_seed


    def create_signal(
            self,
            ts_index: pd.DatetimeIndex,
    ) -> pd.DataFrame:
        CL_type = self.CL_type
        random_delay = self.random_delay
        random_seed = self.random_seed
        periods = periods_from_json(controller_type = CL_type)
        cs_final = convert_periods_to_series(
            ts_index,
            periods = periods,
            random_delay=random_delay,
            random_seed = random_seed,
        )
        return pd.DataFrame(cs_final, index=ts_index, columns=["CS"])
    

@dataclass
class Timer():
    timer_type: str = "timer"
    time_start: float = 0.0
    time_stop: float = 3.0
    random_delay : bool = False
    random_start: float = 0.0
    random_stop: float = 0.0
    random_seed: int = -1

    def create_signal( self, ts_index: pd.DatetimeIndex, ) -> pd.DataFrame:
        timer_type = self.timer_type
        if timer_type in ["timer_SS", "timer_OP"]:
            periods = periods_from_json(controller_type = timer_type)
        else:
            periods = [period_custom(
                time_start = self.time_start,
                time_stop = self.time_stop,
                random_on = self.random_start,
                random_off = self.random_stop
            ),]

        cs_final = convert_periods_to_series(ts_index, periods)
        return pd.DataFrame(cs_final, index=ts_index, columns=["CS"])
    

@dataclass
class Diverter():
    type: str = "diverter"
    time_start: float = 0.
    time_stop: float = 4.
    heater_nom_power:float | None = None


    def create_signal(
            self,
            ts_index: pd.DatetimeIndex,
            pv_power: pd.Series | None = None,
        ) -> pd.DataFrame:

        if self.heater_nom_power is not None:
            heater_nom_power = self.heater_nom_power
        else:
            heater_nom_power = 0.

        periods = [
            period_custom(time_start = self.time_start, time_stop = self.time_stop, ),
        ]
        cs_final = convert_periods_to_series(ts_index, periods)
        ts_control = pd.DataFrame(index=ts_index, columns=["CS"])
        ts_control["CS"] = cs_final
        if pv_power is not None:
            ts_control["CS"] = np.where(
                ts_control["CS"]>=0.99,
                ts_control["CS"],
                np.where(
                    (pv_power > 0) & (pv_power < heater_nom_power),
                    pv_power / heater_nom_power,
                    np.where(pv_power > heater_nom_power, 1., 0.)
                )
            )    
        return ts_control



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
        controller_type: str = "GS",
) -> list[Period]:
    
    file_schedule = os.path.join(DIR_CONTROL, f'{controller_type}.json')
    with open(file_schedule, 'r') as file:
        control_type_data = json.load(file)
    periods = control_type_data["schedule"]
    return periods


def convert_periods_to_series(
        idx: pd.DatetimeIndex,
        periods: list[Period],
        random_delay: bool = False,
        random_seed: int = -1,
) -> pd.Series:

    #TODO check if the .to_list() is working
    month = idx.month.astype(float)
    hour = (idx.hour + idx.minute / 60.0).astype(float)
    freq = pd.to_datetime(idx).freq
    if freq is not None:
        STEP = freq.n

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
        
        #Applying conditions and adding random if needed
        cs_aux = np.zeros(len(idx))
        for (i,case) in enumerate(cases):
            if case:
                cs_aux = np.where(conditions[i], 1, 0)
        
        if random_delay:
            cs_period = add_random_delay(
                cs_aux,
                random_delay_on = int(period["random_on"]),
                random_delay_off = int(period["random_off"]),
                random_seed = random_seed,
                STEP=STEP,
            )
        else:
            cs_period = cs_aux.copy()

        cs_periods = pd.Series(
            np.where(((cs_periods == 1) | (cs_period == 1)), 1, 0)
            , index=idx
        )
    return cs_periods



def add_random_delay(
    cs_no_random: np.ndarray,
    random_delay_on: int = 0,   #[min]
    random_delay_off: int = 0,  #[min]
    STEP: int = 3,              #[min]
    random_seed: int = -1,
) -> np.ndarray:

    if random_seed == -1:
        seed = np.random.SeedSequence().entropy
    else:
        seed = random_seed
    
    # TODO can we use a for loop here? over 1 (starting_times) and -1 (stopping_times)

    switches = np.diff(cs_no_random)   # Values 1=ON, -1=OFF
    index_switch_on = np.where(switches == 1)[0]
    index_switch_off = np.where(switches == -1)[0]

    if len(index_switch_on) == 0 or len(index_switch_off) == 0:
        return cs_no_random

    rng = np.random.default_rng(seed)
    max_delay_on_index = (random_delay_on // STEP) + 1
    max_delay_off_index = (random_delay_off // STEP) + 1

    offsets_on = rng.choice(
        np.arange(0, max_delay_on_index), size=len(index_switch_on),
    )
    offsets_off = rng.choice(
        np.arange(0, max_delay_off_index), size=len(index_switch_off),
    )

    new_index_switch_on = index_switch_on + offsets_on
    if new_index_switch_on[-1] > len(cs_no_random):
        new_index_switch_on[-1] = len(cs_no_random)-1
    new_index_switch_off = index_switch_off + offsets_off
    if new_index_switch_off[-1] > len(cs_no_random):
        new_index_switch_off[-1] = len(cs_no_random)-1
        
    cs_final = np.zeros(len(cs_no_random))
    cs_final[new_index_switch_on] = 1
    cs_final[new_index_switch_off] = -1
    cs_final = cs_no_random[0] + cs_final.cumsum()

    return cs_final


# def load_control_signal(
#         idx: pd.DatetimeIndex,
#         control_type: str = "GS",
#         random_on: bool = True,
#         random_seed: int = -1,
#         timer_start: float = 0.,
#         timer_length: float = 4.,
#         cols: list[str] = SIMULATIONS_IO.TS_TYPES["control"],
# ) -> pd.DataFrame:

#     # retrieving
#     STEP = idx.freq.n

#     # getting data
#     match control_type:
#         case "GS" | "CL1" | "CL2" | "CL3" | "timer_SS" | "timer_OP":
#             periods = periods_from_json(control_type=control_type)

#         case "diverter" | "timer":
#             periods = [ period_custom(
#                             time_start=timer_start,
#                             time_stop = timer_start + timer_length
#                         ), ]
#         case _:
#             raise ValueError(f"{control_type=} not among the valid options: {DEFINITIONS.CONTROL_TYPES=}")

#     cs_no_rand = convert_periods_to_series(idx, periods)
#     if random_on:
#         cs_final = add_random_delay(cs_no_rand, random_seed, STEP=STEP)
#     else:
#         cs_final = cs_no_rand.to_frame().copy()

#     df_control = pd.DataFrame(cs_final, index=idx, columns=cols)
#     return df_control
