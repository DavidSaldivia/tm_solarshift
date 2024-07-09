import os
import json
import numpy as np
import pandas as pd

from tm_solarshift.constants import (
    DEFINITIONS,
    DIRECTORY,
    SIMULATIONS_IO
)
TS_TYPES = SIMULATIONS_IO.TS_TYPES

COLS_CONTROL = TS_TYPES["control"]
CONTROL_TYPES = DEFINITIONS.CONTROL_TYPES
DIR_CONTROL = DIRECTORY.DIR_DATA["control"]

#-------------
def load_schedule(
    ts: pd.DataFrame,
    control_load: int = 0,
    columns: list[str] = COLS_CONTROL,
    random_ON: bool = True,
) -> pd.DataFrame:

    idx = pd.to_datetime(ts.index)
    STEP = idx.freq.n
    df_cs = pd.DataFrame(index=idx, columns=["CS"])
    
    periods = period_definitions(control_load)
    
    # Overwritting randomization to avoid error in function
    if control_load in [-1,0,10]:
        random_ON = False
    
    (df_cs["CS_norand"], df_cs["CS"]) = create_signal_series(
        df_cs, periods, random_ON=random_ON, STEP=STEP
    )
    ts[columns] = df_cs[columns]
    return ts

#--------------------
def add_randomization_delay(
    df_in: pd.DataFrame,
    random_delay_on: int = 0,
    random_delay_off: int = 0,
    STEP: int = 3,
) -> pd.DataFrame:

    """
    This function adds randomization to starting and stopping times in Control Signals
    This function only works if the control signal is integers (1=ON, 0=OFF)
    This function is useful for the TRNSYS Simulations as it is designed to work with the same STEP
    """

    df = df_in.copy()
    df["Switch_no_rand"] = df["CS"].diff()  # Values 1=ON, -1=OFF

    # Defining starting and stoping times without randomness
    df_starts = df[df["Switch_no_rand"] == 1].copy()
    df_starts["start_no_rand"] = df_starts.index
    df_stops = df[df["Switch_no_rand"] == -1].copy()
    df_stops["stop_no_rand"] = df_stops.index

    # Defining on and off delays
    df_starts["delays_on"] = np.random.choice(
        np.arange(0, random_delay_on + 1, STEP),
        size=len(df_starts),
    )
    df_stops["delays_off"] = np.random.choice(
        np.arange(0, random_delay_off + 1, STEP),
        size=len(df_stops)
    )
    #Last delays are =0 to avoid get outside indexes
    df_starts.iloc[-1, df_starts.columns.get_loc("delays_on")] = 0
    df_stops.iloc[-1, df_stops.columns.get_loc("delays_off")] = 0
    # Defining starting and stopping times once randomization is applied
    df_starts["start_with_rand"] = df_starts.apply(
        lambda aux: aux["start_no_rand"] 
        + pd.offsets.Minute(aux["delays_on"]),
        axis=1
    )
    df_stops["stop_with_rand"] = df_stops.apply(
        lambda aux: aux["stop_no_rand"] 
        + pd.offsets.Minute(aux["delays_off"]),
        axis=1,
    )
    # Applying the randomization into the final dataframe
    df["Switch_rand"] = 0
    df.loc[df_starts["start_with_rand"], "Switch_rand"] = 1
    df.loc[df_stops["stop_with_rand"], "Switch_rand"] = -1
    output = (df.iloc[0]["CS"] + df["Switch_rand"].cumsum())
    return output

#----------------
def create_signal_series(
    df_cs_original: pd.DataFrame,
    periods: list,
    STEP: int = 3,
    random_ON: bool = True,
) -> list[pd.Series]:

    df_cs = df_cs_original.copy()
    df_cs["CS"] = 0  # Without randomization
    df_cs["CS2"] = 0  # With randomization

    idx = pd.DatetimeIndex(df_cs.index)
    month = idx.month
    hour = idx.hour + idx.minute / 60.0

    for period in periods:

        df_period = df_cs.copy()

        # There are four cases:
        # 1.   (start_month <= stop_month) & (start_time <= stop_time)
        # 2.   (start_month >  stop_month) & (start_time <= stop_time)
        # 3.   (start_month <= stop_month) & (start_time >  stop_time)
        # 4.   (start_month >  stop_month) & (start_time >  stop_time)

        if (period["month_start"] <= period["month_stop"]) and (
            period["time_start"] <= period["time_stop"]
        ):
            # print('Condition 1')
            df_period["CS"] = np.where(
                (
                    ((month >= period["month_start"]) 
                    & (month <= period["month_stop"])
                    )
                    & ((hour >= period["time_start"]) 
                    & (hour <= period["time_stop"])
                    )
                ),
                1,
                0,
            )

        if (period["month_start"] > period["month_stop"]) and (
            period["time_start"] <= period["time_stop"]
        ):
            # print('Condition 2')
            df_period["CS"] = np.where(
                (
                    ((month >= period["month_start"]) 
                    | (month <= period["month_stop"])
                    )
                    & ((hour >= period["time_start"]) 
                    & (hour <= period["time_stop"])
                    )
                ),
                1,
                0,
            )

        if (period["month_start"] <= period["month_stop"]) and (
            period["time_start"] > period["time_stop"]
        ):
            # print('Condition 3')
            df_period["CS"] = np.where(
                (
                    ((month >= period["month_start"]) & (month <= period["month_stop"]))
                    & ((hour >= period["time_start"]) | (hour <= period["time_stop"]))
                ),
                1,
                0,
            )

        if (period["month_start"] > period["month_stop"]) and (
            period["time_start"] > period["time_stop"]
        ):
            # print('Condition 4')
            df_period["CS"] = np.where(
                (
                    ((month >= period["month_start"]) | (month <= period["month_stop"]))
                    & ((hour >= period["time_start"]) | (hour <= period["time_stop"]))
                ),
                1,
                0,
            )

        # Adding the randomization associated with the period
        if random_ON and sum(df_period["CS"]==1)>0:
            df_period["CS2"] = add_randomization_delay(
                df_period,
                random_delay_on=period["random_on"],
                random_delay_off=period["random_off"],
                STEP=STEP,
            )
        else:
            df_period["CS2"] = df_period["CS"]

        # Joining the different periods
        df_cs["CS"] = np.where(((df_cs["CS"] == 1) | (df_period["CS"] == 1)), 1, 0)

        # Joining the different periods
        df_cs["CS2"] = np.where(((df_cs["CS2"] == 1) | (df_period["CS2"] == 1)), 1, 0)

    return [df_cs["CS"], df_cs["CS2"]]

#---------------------------------
def period_definitions(profile_control):

    if profile_control == -1:
        # No Connection at all (useful for tests)
        periods = [
            {
                "label": "annual",  # only used as reference
                "month_start": 0,  # inclusive
                "month_stop": 0,  # inclusive
                "time_start": 0,  # inclusive
                "time_stop": 0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            }
        ]
    
    elif profile_control == 0:
        # 24/7 General Supply
        periods = [
            {
                "label": "annual",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": 0.0,  # inclusive
                "time_stop": 25.0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            }
        ]
    
    elif profile_control == 1:
        # Ausgrid's Controlled Load 1 (Legacy)
        periods = [
            {
                "label": "winter",  # only used as reference
                "month_start": 4,  # inclusive
                "month_stop": 9,  # inclusive
                "time_start": 22.0,  # inclusive
                "time_stop": 7.0,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 0,  # [mins]
            },
            {
                "label": "summer",  # only used as reference
                "month_start": 10,  # inclusive
                "month_stop": 3,  # inclusive
                "time_start": 21.0,  # inclusive
                "time_stop": 6.0,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 0,  # [mins]
            },
        ]
    
    elif profile_control == 2:
        # Ausgrid's Controlled Load 2 (Legacy - Option A)
        periods = [
            {
                "label": "winter",  # only used as reference
                "month_start": 4,  # inclusive
                "month_stop": 9,  # inclusive
                "time_start": 20.0,  # inclusive
                "time_stop": 17.0,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 0,  # [mins]
            },
            {
                "label": "spring",  # only used as reference
                "month_start": 10,  # inclusive
                "month_stop": 10,  # inclusive
                "time_start": 19.0,  # inclusive
                "time_stop": 16.0,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 0,  # [mins]
            },
            {
                "label": "summer",  # only used as reference
                "month_start": 11,  # inclusive
                "month_stop": 3,  # inclusive
                "time_start": 19.0,  # inclusive
                "time_stop": 14.0,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 0,  # [mins]
            },
        ]
    
    elif profile_control == 3:
        # Ausgrid's new Controlled Load 1 (Solar Soak - Option B)
        # Here is called CL3
        periods = [
            {
                "label": "winter_night",  # only used as reference
                "month_start": 4,  # inclusive
                "month_stop": 9,  # inclusive
                "time_start": 22.0,  # inclusive
                "time_stop": 6.75,  # inclusive
                "random_on": 210,  # [mins]
                "random_off": 15,  # [mins]
            },
            {
                "label": "winter_day",  # only used as reference
                "month_start": 4,  # inclusive
                "month_stop": 9,  # inclusive
                "time_start": 10.0,  # inclusive
                "time_stop": 16.75,  # inclusive
                "random_on": 210,  # [mins]
                "random_off": 15,  # [mins]
            },
            {
                "label": "spring_night",  # only used as reference
                "month_start": 10,  # inclusive
                "month_stop": 10,  # inclusive
                "time_start": 21.0,  # inclusive
                "time_stop": 4.25,  # inclusive
                "random_on": 210,  # [mins]
                "random_off": 15,  # [mins]
            },
            {
                "label": "spring_day",  # only used as reference
                "month_start": 10,  # inclusive
                "month_stop": 10,  # inclusive
                "time_start": 9.0,  # inclusive
                "time_stop": 15.75,  # inclusive
                "random_on": 210,  # [mins]
                "random_off": 15,  # [mins]
            },
            {
                "label": "summer_night",  # only used as reference
                "month_start": 11,  # inclusive
                "month_stop": 3,  # inclusive
                "time_start": 21.0,  # inclusive
                "time_stop": 5.75,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 15,  # [mins]
            },
            {
                "label": "summer_day",  # only used as reference
                "month_start": 11,  # inclusive
                "month_stop": 3,  # inclusive
                "time_start": 9.0,  # inclusive
                "time_stop": 13.50,  # inclusive
                "random_on": 180,  # [mins]
                "random_off": 15,  # [mins]
            },
        ]
    
    elif profile_control == 4:
        # Solar soak, no randomization, only solar time
        periods = [
            {
                "label": "year",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": 9.0,  # inclusive
                "time_stop": 15.0,  # inclusive
                "random_on": 0.0,  # [mins]
                "random_off": 0.0,  # [mins]
            }
        ]
    
    elif profile_control == 5:
        # Old control load 3 (CL1 + Solar time). No randomization
        periods = [
            {
                "label": "year_night",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": 22.0,  # inclusive
                "time_stop": 7.0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            },
            {
                "label": "year_day",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": 9.0,  # inclusive
                "time_stop": 15.0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            },
        ]

    elif profile_control == 6:
        # Timer using off-peak periods
        periods = [
            {
                "label": "null",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": 22.0,  # inclusive
                "time_stop": 24.0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            },
            {
                "label": "null",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": 0.0,  # inclusive
                "time_stop": 7.0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            },
        ]
    
    elif profile_control == 10:
        # Only 3 hours at beginning of day (for Event's analysis)
        periods = [
            {
                "label": "annual",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": 0.0,  # inclusive
                "time_stop": 3.0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            }
        ]
        
    elif profile_control in range(100,121):
        timer_on = profile_control - 100.0
        timer_off = timer_on + 4.0
        periods = [
            {
                "label": "annual",  # only used as reference
                "month_start": 1,  # inclusive
                "month_stop": 12,  # inclusive
                "time_start": timer_on,  # inclusive
                "time_stop": timer_off,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            }
        ]

    else:
        # No Connection at all (useful for tests)
        periods = [
            {
                "label": "annual",  # only used as reference
                "month_start": 0,  # inclusive
                "month_stop": 0,  # inclusive
                "time_start": 0,  # inclusive
                "time_stop": 0,  # inclusive
                "random_on": 0,  # [mins]
                "random_off": 0,  # [mins]
            }
        ]
    return periods

def period_custom(
    label: str = "annual",
    month_start: int = 1,
    month_stop: int = 12,
    time_start: float = 0.0,
    time_stop: float = 3.0,
    random_on: float = 0.,
    random_off: float = 0.,
) -> dict:
    period = {
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
) -> list[dict[str,str|int|float]]:
    
    file_schedule = os.path.join(DIR_CONTROL, f'{control_type}.json')
    with open(file_schedule, 'r') as file:
        control_type_data = json.load(file)
    periods = control_type_data["schedule"]
    
    return periods

#--------------------------
def load_control_signal(
        idx: pd.DatetimeIndex,
        control_type: str = "GS",
        random_on: bool = True,
        random_seed: int = -1,
        timer_start: float = 0.,
        timer_length: float = 4.,
        cols: list[str] = COLS_CONTROL,
) -> pd.DataFrame:

    # checking
    if control_type not in CONTROL_TYPES:
        raise ValueError(f"{control_type=} not among the valid options: {CONTROL_TYPES=}")

    # retrieving
    STEP = idx.freq.n

    # getting data
    match control_type:
        case "GS" | "CL1" | "CL2" | "CL3" | "timer_SS" | "timer_OP":
            periods = periods_from_json(control_type=control_type)

        case "diverter" | "timer":
            periods = [
                period_custom(
                    time_start=timer_start, time_stop=timer_start + timer_length
                ),
            ]
        case _:
            raise ValueError(f"{control_type=} not among the valid options: {CONTROL_TYPES=}")

    cs_periods = convert_periods_to_series(idx, periods)
    if random_on:
        cs_final = add_random_delay(cs_periods, random_seed, STEP=STEP)
    else:
        cs_final = cs_periods

    cs = pd.DataFrame(cs_final, index=idx, columns=cols)
    return cs

#----------------------------
def convert_periods_to_series(
        idx: pd.DatetimeIndex,
        periods: list[dict[str,int|float]],
) -> pd.Series:

    month = idx.month
    hour = idx.hour + idx.minute / 60.0

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

    if seed_id == -1:
        seed = np.random.SeedSequence().entropy
    else:
        seed = seed_id
    
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(cs_periods, columns=["CS"])
    df["switch_no_rand"] = df["CS"].diff()  # Values 1=ON, -1=OFF

    # Defining starting and stoping times without randomisation
    df_starts = df[df["switch_no_rand"] == 1].copy()
    df_starts["start_no_rand"] = df_starts.index
    df_stops = df[df["switch_no_rand"] == -1].copy()
    df_stops["stop_no_rand"] = df_stops.index

    # Defining on and off delays
    df_starts["delays_on"] = rng.choice(
        np.arange(0, random_delay_on + 1, STEP),
        size=len(df_starts),
    )
    df_stops["delays_off"] = rng.choice(
        np.arange(0, random_delay_off + 1, STEP),
        size=len(df_stops)
    )
    #Last delays are = 0 to avoid get outside indexes
    df_starts.iloc[-1, df_starts.columns.get_loc("delays_on")] = 0
    df_stops.iloc[-1, df_stops.columns.get_loc("delays_off")] = 0

    # Defining starting and stopping times once randomization is applied
    df_starts["start_with_rand"] = df_starts.apply(
        lambda aux: aux["start_no_rand"] 
        + pd.offsets.Minute(aux["delays_on"]),
        axis=1
    )
    df_stops["stop_with_rand"] = df_stops.apply(
        lambda aux: aux["stop_no_rand"] 
        + pd.offsets.Minute(aux["delays_off"]),
        axis=1,
    )
    # Applying the randomization into the final dataframe
    df["switch_rand"] = 0
    df.loc[df_starts["start_with_rand"], "switch_rand"] = 1
    df.loc[df_stops["stop_with_rand"], "switch_rand"] = -1
    output = (df.iloc[0]["CS"] + df["switch_rand"].cumsum())
    return output

#-------------------
def main():

    #Creating a ts dataframe
    import tm_solarshift.timeseries.control as control
    from tm_solarshift.general import Simulation
    sim = Simulation()

    control_load = sim.household.control_load
    ts = sim.create_ts()
    
    #Creating a schedule Control timeseries
    ts_CL1 = control.load_schedule(ts, control_load = control_load)
    ts_CL1_norand = control.load_schedule(ts, control_load = control_load, random_ON=False)

    COLS = TS_TYPES["control"]
    print(ts_CL1[COLS])
    print(ts_CL1_norand[COLS])

    return


if __name__ == "__main__":
    main()
    pass