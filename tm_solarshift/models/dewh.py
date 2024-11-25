from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Protocol, Self

from tm_solarshift.utils.units import Variable, Water
from tm_solarshift.constants import DIRECTORY
from tm_solarshift.models.trnsys import TrnsysDEWH

# Protocols for DEWH
class DEWH(Protocol):
    @classmethod
    def from_model_file(cls, file_path: str, model: str) -> Self:
        ...
    def run_thermal_model(self, ts: pd.DataFrame, verbose: bool) -> pd.DataFrame:
        ...

FILES_MODEL_SPECS = DIRECTORY.FILES_MODEL_SPECS

class HWTank():
    """The base class for all heaters with tank.

    Parameters:

    """

    def __init__(self):
        self.label = "hwtank"
        self.nom_power = Variable(None, "W")
        self.nom_power_th = Variable(None, "W")
        self.eta = Variable(None, "-")

        # tank geometry and losses
        self.vol = Variable(0.315,"m3")
        self.height = Variable(1.45, "m")  # It says 1.640 in specs, but it is external height, not internal
        self.height_inlet = Variable(0.113, "m")
        self.height_outlet = Variable(1.317, "m")
        self.height_heater = Variable(0.103, "m")
        self.height_thermostat = Variable(0.103, "m")
        self.U = Variable(0.9, "W/m2-K")
        self.fluid = Water()

        #numerical simulation
        self.nodes = 10     # Tank nodes. DO NOT CHANGE, unless TRNSYS layout is changed too!
        self.temps_ini = 3  # [-] Initial temperature of the tank. Check trnsys.editing_dck_tank() for options

        # control
        self.temp_max = Variable(65.0, "degC")  #Maximum temperature in the tank
        self.temp_deadband = Variable(10.0, "degC") # Dead band for max temp control
        self.temp_min = Variable(45.0, "degC")  # Minimum temperature in the tank
        self.temp_consump = Variable(45.0, "degC") #Consumption temperature
    
    @property
    def thermal_cap(self) -> Variable:
        vol = self.vol.get_value("m3")
        rho = self.fluid.rho.get_value("kg/m3")
        cp = self.fluid.cp.get_value("J/kg-K")
        temp_max = self.temp_max.get_value("degC")
        temp_min = self.temp_min.get_value("degC")
        thermal_cap = vol * (rho * cp) * (temp_max - temp_min) / 3.6e6
        return Variable( thermal_cap, "kWh")

    @property
    def diam(self) -> Variable:
        vol = self.vol.get_value("m3")
        height = self.height.get_value("m")
        diam = (4 * vol / np.pi / height) ** 0.5
        return Variable( diam , "m" )
    
    @property
    def area_loss(self) -> Variable:
        diam = self.diam.get_value("m")
        height = self.height.get_value("m")
        area_loss = np.pi * diam * (diam / 2 + height)
        return Variable( area_loss, "m2" ) 
    
    @property
    def temp_high_control(self) -> Variable:
        temp_max = self.temp_max.get_value("degC")
        temp_deadband = self.temp_deadband.get_value("degC")
        temp_high_control = temp_max - temp_deadband / 2.0
        return Variable(temp_high_control, "degC")


class ResistiveSingle(HWTank):
    """The model for a hot water tank with a single immersive resistive heater.

    Args:
        HWTank (HWTank): Hot water tank
    """
    def __init__(self):
        super().__init__()
        # description
        self.name = "Conventional resistive immersive heater (single unit)."
        self.label = "resistive"
        self.model = "-"
        self.cost = Variable(np.nan, "AUD")
        # heater data
        self.nom_power = Variable(3600.0, "W")
        self.eta = Variable(1.0, "-")

    def __eq__(self, other) : 
            return self.__dict__ == other.__dict__

    @classmethod
    def from_model_file(
        cls,
        file_path: str = FILES_MODEL_SPECS["resistive"],
        model:str = "",
    ):
        df = pd.read_csv(file_path, index_col=0)
        specs = pd.Series(df.loc[model])
        units = pd.Series(df.loc["units"])
        output = cls()
        output.model = model
        for (lbl,value) in specs.items():
            unit = units[str(lbl)]
            try:
                value = float(value)
            except:
                pass          
            setattr(output, str(lbl), Variable(value, unit) )
        return output
    
    def run_thermal_model(
            self,
            ts: pd.DataFrame,
            verbose: bool = False,
    ) -> pd.DataFrame:
        trnsys_dewh = TrnsysDEWH(DEWH=self, ts=ts)
        df_tm = trnsys_dewh.run_simulation(verbose=verbose)
        return df_tm


class HeatPump(HWTank):
    def __init__(self):
        # description
        super().__init__()
        self.name = "Heat Pump, external heat exchanger with thermostat."
        self.label = "heat_pump"
        self.model = "-"
        self.cost = Variable(np.nan, "AUD")
        # heater
        self.nom_power_th = Variable(5240.0, "W")
        self.nom_power_el = Variable(870.0, "W")
        self.eta = Variable(6.02, "-")
        self.nom_tamb = Variable(32.6, "degC")
        self.nom_tw = Variable(21.1, "degC")


    @classmethod
    def from_model_file(
        cls,
        file_path: str = FILES_MODEL_SPECS["heat_pump"],
        model: str = "",
        ):
        df = pd.read_csv(file_path, index_col=0)
        specs = pd.Series(df.loc[model])
        units = pd.Series(df.loc["units"])
        output = cls()
        for (lbl,value) in specs.items():
            unit = units[str(lbl)]
            try:
                value = float(value)
            except:
                pass          
            setattr(output, str(lbl), Variable(value, unit) )
        return output
    
    
    def run_thermal_model(
            self,
            ts: pd.DataFrame,
            verbose: bool = False,
    ) -> pd.DataFrame:
        from tm_solarshift.models.trnsys import TrnsysDEWH
        trnsys_dewh = TrnsysDEWH(DEWH=self, ts=ts)
        df_tm = trnsys_dewh.run_simulation(verbose=verbose)
        return df_tm