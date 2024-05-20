import numpy as np
import pandas as pd

from tm_solarshift.constants import DEFAULT
from tm_solarshift.general import Simulation
from tm_solarshift.devices import SolarThermalElecAuxiliary
from tm_solarshift.models import postprocessing
from tm_solarshift.utils.units import conversion_factor as CF
from tm_solarshift.models import trnsys
from tm_solarshift.utils.solar import (get_plane_irradiance, get_plane_angles)
DEFAULT_TZ = DEFAULT.TZ

def run_thermal_model(
        simulation: Simulation,
        ts: pd.DataFrame = None,
        verbose: bool = False,
        tz: str = DEFAULT_TZ,
) -> tuple[pd.DataFrame, dict[str,float]]:
    
    STEP_h = simulation.simulation.STEP.get_value("hr")

    #Running a trnsys simulation assuming all energy from resistive
    out_all = trnsys.run_simulation(simulation, ts, verbose=verbose)
    out_overall = postprocessing.annual_postproc(simulation, ts, out_all)

    #Calculating energy provided by solar thermal and the solar fraction
    #Emissions and tariffs are recalculated

    DEWH: SolarThermalElecAuxiliary = simulation.DEWH
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

    temp_amb = out_all["temp_amb"]
    temp_inlet = out_all["Node10"]

    plane_irrad = get_plane_irradiance(ts, latitude, longitude, tilt, orient, tz)
    plane_irrad.index = plane_irrad.index.tz_localize(None)
    plane_angles = get_plane_angles(ts, latitude, longitude, tilt, orient, tz)
    plane_angles.index = plane_angles.index.tz_localize(None)
    cosine_aoi = plane_angles["cosine_aoi"]
    
    out_all["total_irrad"] = plane_irrad["poa_global"] * area         #["W"]
    out_all["cosine_aoi"] = np.where( cosine_aoi>0.0 , cosine_aoi, 0.)
    out_all["iam"] = np.where( cosine_aoi>0.0 , 1. - IAM * (1./cosine_aoi - 1.), 0.)


    out_all["heater_perf"] = np.where(
        out_all["total_irrad"] > 0.,
        FRta - FRUL * (temp_inlet - temp_amb) / out_all["total_irrad"],
        0.
    )
    out_all["heater_perf"] = np.where(
        (out_all["heater_perf"] > 0.) & (out_all["heater_perf"]<=1.0),
        out_all["heater_perf"],
        0.
    )
    out_all["solar_energy_u"] = out_all["heater_perf"] * out_all["total_irrad"]  #["W"]

    out_overall["solar_energy_u"] = (out_all["solar_energy_u"] * STEP_h * CF("Wh", "kWh")).sum()
    out_overall["solar_energy_in"] = (out_all["total_irrad"] * STEP_h * CF("Wh", "kWh")).sum()
    out_overall["solar_ratio"] =  out_overall["solar_energy_u"] / out_overall["heater_heat_acum"]
    out_overall["heater_perf_avg"] = out_overall["solar_energy_u"] / out_overall["solar_energy_in"]

    temp_outlet = temp_inlet + out_all["solar_energy_u"] / (massflowrate * cp)

    #Recalculate total emissions and tariffs
    out_all["heater_power_no_solar"] = ( out_all["heater_power"] - out_all["solar_energy_u"] * CF("W","kJ/h") )
    out_overall["emissions_total"] = (
        (out_all["heater_power_no_solar"] * CF("kJ/h", "MW")) * STEP_h
        * ts["intensity_index"]
        ).sum()
    out_overall["emissions_marginal"] = (
        (out_all["heater_power_no_solar"] * CF("kJ/h", "MW")) * STEP_h
        * ts["marginal_index"]
        ).sum()
    out_overall["heater_power_acum"] = (out_overall["heater_power_acum"] - out_overall["solar_energy_u"])

    return (out_all, out_overall)