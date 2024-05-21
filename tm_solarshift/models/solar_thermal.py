from __future__ import annotations
import numpy as np
import pandas as pd
from typing import TYPE_CHECKING, Optional

from tm_solarshift.constants import (DIRECTORY, DEFAULT)
from tm_solarshift.utils.units import (Variable, conversion_factor as CF, Water)
from tm_solarshift.utils.solar import (get_plane_irradiance, get_plane_angles)

if TYPE_CHECKING:
    from tm_solarshift.general import Simulation

FILES_MODEL_SPECS = DIRECTORY.FILES_MODEL_SPECS
DEFAULT_TZ = DEFAULT.TZ

#-------------------
class SolarThermalElecAuxiliary():
    def __init__(self):

        # description
        self.name = "Solar thermal colector. Tank separated from collector, with electric heater."
        self.label = "solar_thermal"
        self.model = "-"
        self.cost = Variable(np.nan, "AUD")
        
        #Nominal values
        self.massflowrate = Variable(0.05, "kg/s")
        self.fluid = Water()
        self.area = Variable(2.0, "m2")
        self.FRta = Variable(0.6, "-")
        self.FRUL = Variable(3.0, "W/m2-K")
        self.IAM = Variable(0.05, "-")
        self.lat = Variable(-33.86,"-")
        self.lon = Variable(151.22,"-")
        self.tilt = Variable(abs(self.lat.get_value("-")),"-")
        self.orient = Variable(180.0,"-")
    
        # Auxiliary resistive heater
        self.nom_power = Variable(3600.0, "W")
        self.eta = Variable(1.0, "-")

        # tank
        self.vol = Variable(0.315,"m3")
        self.height = Variable(1.45, "m")  # It says 1.640 in specs, but it is external height, not internal
        self.height_inlet = Variable(0.113, "m")
        self.height_outlet = Variable(1.317, "m")
        self.height_heater = Variable(0.103, "m")
        self.height_thermostat = Variable(0.103, "m")
        self.U = Variable(0.9, "W/m2-K")
        self.nodes = 10     # Tank nodes. DO NOT CHANGE, unless TRNSYS layout is changed too!
        self.temps_ini = 3  # [-] Initial temperature of the tank. Check editing_dck_tank() below for the options
        self.fluid = Water()

        #control
        self.temp_max = Variable(63.0, "degC")  #Maximum temperature in the tank
        self.temp_min = Variable(45.0,"degC")  # Minimum temperature in the tank
        self.temp_high_control = Variable(59.0, "degC")  #Temperature to for control
        self.temp_consump = Variable(45.0, "degC") #Consumption temperature
        self.temp_deadband = Variable(10, "degC")

    @property
    def thermal_cap(self):
        from tm_solarshift.models.dewh import tank_thermal_capacity
        return tank_thermal_capacity(self)
    @property
    def diam(self):
        from tm_solarshift.models.dewh import tank_diameter
        return tank_diameter(self)
    @property
    def area_loss(self):
        from tm_solarshift.models.dewh import tank_area_loss
        return tank_area_loss(self)

    @classmethod
    def from_model_file(
        cls,
        file_path: str = FILES_MODEL_SPECS["solar_thermal"],
        model:str = "",
        ):
        
        df = pd.read_csv(file_path, index_col=0)
        specs = pd.Series(df.loc[model])
        units = pd.Series(df.loc["units"])
        
        output = cls()
        for (lbl,value) in specs.items():
            unit = units[lbl]
            try:
                value = float(value)
            except:
                pass
            setattr(output, lbl, Variable(value, unit) )
        return output


    # def run_thermal_model(
    #         self,
    #         ts: pd.DataFrame,
    #         verbose: bool = False,
    #         tz: str = DEFAULT_TZ,
    # ) -> pd.DataFrame:
        
    #     STEP_h = pd.to_datetime(ts.index).freq.n

    #     from tm_solarshift.models import trnsys
    #     from tm_solarshift.models import postprocessing

    #     #Running a trnsys simulation assuming all energy from resistive
    #     trnsys_dewh = trnsys.TrnsysDEWH(DEWH=self, ts=ts)
    #     df_tm = trnsys_dewh.run_simulation(ts, verbose=verbose)

    #     # Calculating energy provided by solar thermal and the solar fraction
    #     # Emissions and tariffs are recalculated
    #     massflowrate = self.massflowrate.get_value("kg/s")
    #     area = self.area.get_value("m2")
    #     FRta = self.FRta.get_value("-")
    #     FRUL = self.FRUL.get_value("W/m2-K")
    #     latitude = self.lat.get_value("-")
    #     longitude = self.lon.get_value("-")
    #     tilt = self.tilt.get_value("-")
    #     orient = self.orient.get_value("-")
    #     cp = self.fluid.cp.get_value("J/kg-K")
    #     IAM = self.IAM.get_value("-")

    #     temp_amb = df_tm["temp_amb"]
    #     temp_inlet = df_tm["Node10"]

    #     ts_index = pd.to_datetime(ts.index)
    #     plane_irrad = get_plane_irradiance(ts, latitude, longitude, tilt, orient, tz)
    #     plane_irrad.index = ts_index.tz_localize(None)
    #     plane_angles = get_plane_angles(ts, latitude, longitude, tilt, orient, tz)
    #     plane_angles.index = ts_index.tz_localize(None)
    #     cosine_aoi = plane_angles["cosine_aoi"]
        
    #     df_tm["total_irrad"] = plane_irrad["poa_global"] * area         #["W"]
    #     df_tm["cosine_aoi"] = np.where( cosine_aoi>0.0 , cosine_aoi, 0.)
    #     df_tm["iam"] = np.where( cosine_aoi>0.0 , 1. - IAM * (1./cosine_aoi - 1.), 0.)

    #     df_tm["heater_perf"] = np.where(
    #         df_tm["total_irrad"] > 0.,
    #         FRta - FRUL * (temp_inlet - temp_amb) / df_tm["total_irrad"],
    #         0.
    #     )
    #     df_tm["heater_perf"] = np.where(
    #         (df_tm["heater_perf"] > 0.) & (df_tm["heater_perf"]<=1.0),
    #         df_tm["heater_perf"],
    #         0.
    #     )
    #     df_tm["solar_energy_u"] = df_tm["heater_perf"] * df_tm["total_irrad"]  #["W"]
    #     return df_tm


def run_thermal_model(
        sim: Simulation,
        ts: Optional[pd.DataFrame] = None,
        verbose: bool = False,
        tz: str = DEFAULT_TZ,
) -> tuple[pd.DataFrame, dict[str,float]]:
    
    if ts is None:
        ts = sim.create_ts()
    STEP_h = sim.thermal_sim.STEP.get_value("hr")

    #Running a trnsys simulation assuming all energy from resistive
    from tm_solarshift.models import trnsys
    from tm_solarshift.models import postprocessing
    trnsys_dewh = trnsys.TrnsysDEWH(DEWH=sim.DEWH, ts=ts)
    df_tm = trnsys_dewh.run_simulation(ts, verbose=verbose)
    out_overall = postprocessing.annual_postproc(sim, ts, df_tm)

    #Calculating energy provided by solar thermal and the solar fraction
    #Emissions and tariffs are recalculated

    DEWH: SolarThermalElecAuxiliary = sim.DEWH
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

    temp_amb = df_tm["temp_amb"]
    temp_inlet = df_tm["Node10"]

    ts_index = pd.to_datetime(ts.index)
    plane_irrad = get_plane_irradiance(ts, latitude, longitude, tilt, orient, tz)
    plane_irrad.index = ts_index.tz_localize(None)
    plane_angles = get_plane_angles(ts, latitude, longitude, tilt, orient, tz)
    plane_angles.index = ts_index.tz_localize(None)
    cosine_aoi = plane_angles["cosine_aoi"]
    
    df_tm["total_irrad"] = plane_irrad["poa_global"] * area         #["W"]
    df_tm["cosine_aoi"] = np.where( cosine_aoi>0.0 , cosine_aoi, 0.)
    df_tm["iam"] = np.where( cosine_aoi>0.0 , 1. - IAM * (1./cosine_aoi - 1.), 0.)

    df_tm["heater_perf"] = np.where(
        df_tm["total_irrad"] > 0.,
        FRta - FRUL * (temp_inlet - temp_amb) / df_tm["total_irrad"],
        0.
    )
    df_tm["heater_perf"] = np.where(
        (df_tm["heater_perf"] > 0.) & (df_tm["heater_perf"]<=1.0),
        df_tm["heater_perf"],
        0.
    )
    df_tm["solar_energy_u"] = df_tm["heater_perf"] * df_tm["total_irrad"]  #["W"]

    out_overall["solar_energy_u"] = (df_tm["solar_energy_u"] * STEP_h * CF("Wh", "kWh")).sum()
    out_overall["solar_energy_in"] = (df_tm["total_irrad"] * STEP_h * CF("Wh", "kWh")).sum()
    out_overall["solar_ratio"] =  out_overall["solar_energy_u"] / out_overall["heater_heat_acum"]
    out_overall["heater_perf_avg"] = out_overall["solar_energy_u"] / out_overall["solar_energy_in"]

    temp_outlet = temp_inlet + df_tm["solar_energy_u"] / (massflowrate * cp)

    #Recalculate total emissions and tariffs
    df_tm["heater_power_no_solar"] = ( df_tm["heater_power"] - df_tm["solar_energy_u"] * CF("W","kJ/h") )
    out_overall["emissions_total"] = (
        (df_tm["heater_power_no_solar"] * CF("kJ/h", "MW")) * STEP_h
        * ts["intensity_index"]
        ).sum()
    out_overall["emissions_marginal"] = (
        (df_tm["heater_power_no_solar"] * CF("kJ/h", "MW")) * STEP_h
        * ts["marginal_index"]
        ).sum()
    out_overall["heater_power_acum"] = (out_overall["heater_power_acum"] - out_overall["solar_energy_u"])

    return (df_tm, out_overall)