import numpy as np
import pandas as pd

from tm_solarshift.general import GeneralSetup
from tm_solarshift.devices import SolarThermalElecAuxiliary
from tm_solarshift.utils import postprocessing
from tm_solarshift.utils.units import conversion_factor as CF
from tm_solarshift.thermal_models import (trnsys)
from tm_solarshift.external.pvlib_utils import (
    get_irradiance_plane,
    get_incidence_angle_cosine,
    load_trnsys_weather,
)

def run_thermal_model(
        GS: GeneralSetup,
        ts: pd.DataFrame = None,
        verbose: bool = False,
        STEP_h: float = 3./60.,
) -> pd.DataFrame:
    

    #Running a trnsys simulation assuming all energy from resistive
    out_all = trnsys.run_simulation(GS, ts, verbose=verbose)
    out_overall = postprocessing.annual_simulation(GS, ts, out_all)

    #Calculating energy provided by solar thermal and the solar fraction
    #Emissions and tariffs are recalculated

    DEWH: SolarThermalElecAuxiliary = GS.DEWH
    massflowrate = DEWH.massflowrate.get_value("kg/s")
    area = DEWH.area.get_value("m2")
    FRta = DEWH.FRta.get_value("-")
    FRUL = DEWH.FRUL.get_value("W/m2-K")
    latitude = DEWH.lat.get_value("-")
    longitude = DEWH.lon.get_value("-")
    tilt = DEWH.tilt.get_value("-")
    orient = DEWH.orient.get_value("-")
    cp = DEWH.fluid.cp.get_value("J/kg-K")
    IAM = DEWH.IAM.get_value("-")

    ts_weather = load_trnsys_weather()          #Fix this!
    total_irrad = get_irradiance_plane(ts_weather, latitude, longitude, tilt, orient)
    total_irrad.index = total_irrad.index.tz_localize(None)
    out_all["total_irrad"] = total_irrad * area         #["W"]
    cosine_aoi = get_incidence_angle_cosine(ts, latitude, longitude, tilt, orient)
    out_all["cosine_aoi"] = np.where(cosine_aoi>0.0, cosine_aoi, 0.)
    out_all["iam"] = np.where(cosine_aoi>0.0, 1. - IAM * (1./cosine_aoi - 1.), 0.)

    temp_amb = out_all["T_amb"]
    temp_inlet = out_all["Node10"]

    # out_all["HeaterPerf"] = np.where(
    #     out_all["total_irrad"] > 0.,
    #     FRta * out_all["iam"] - FRUL * (temp_inlet - temp_amb) / out_all["total_irrad"],
    #     0.
    # )
    out_all["HeaterPerf"] = np.where(
        out_all["total_irrad"] > 0.,
        FRta - FRUL * (temp_inlet - temp_amb) / out_all["total_irrad"],
        0.
    )
    out_all["HeaterPerf"] = np.where(
        (out_all["HeaterPerf"] > 0.) & (out_all["HeaterPerf"]<=1.0),
        out_all["HeaterPerf"],
        0.
    )
    out_all["solar_energy_u"] = out_all["HeaterPerf"] * out_all["total_irrad"]  #["W"]

    out_overall["solar_energy_u"] = (out_all["solar_energy_u"] * STEP_h * CF("Wh", "kWh")).sum()
    out_overall["solar_energy_in"] = (out_all["total_irrad"] * STEP_h * CF("Wh", "kWh")).sum()
    out_overall["solar_ratio"] =  out_overall["solar_energy_u"] / out_overall["heater_heat_acum"]
    out_overall["heater_perf_avg"] = out_overall["solar_energy_u"] / out_overall["solar_energy_in"]

    temp_outlet = temp_inlet + out_all["solar_energy_u"] / (massflowrate * cp)

    #Recalculate total emissions and tariffs
    out_all["HeaterPower_no_solar"] = ( out_all["HeaterPower"] - out_all["solar_energy_u"] * CF("W","kJ/h") )
    out_overall["emissions_total"] = (
        (out_all["HeaterPower_no_solar"] * CF("kJ/h", "MW")) * STEP_h
        * ts["Intensity_Index"]
        ).sum()
    out_overall["emissions_marginal"] = (
        (out_all["HeaterPower_no_solar"] * CF("kJ/h", "MW")) * STEP_h
        * ts["Marginal_Index"]
        ).sum()
    out_overall["heater_power_acum"] = (out_overall["heater_power_acum"] - out_overall["solar_energy_u"])

    # print(out_overall)
    return (out_all, out_overall)