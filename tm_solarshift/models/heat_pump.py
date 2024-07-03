from __future__ import annotations
import numpy as np
import pandas as pd
from typing import TYPE_CHECKING, TypeAlias

from tm_solarshift.constants import DIRECTORY
from tm_solarshift.utils.units import (Variable, Water)
from tm_solarshift.models.hw_tank import (
    HWTank,
    tank_thermal_capacity,
    tank_diameter,
    tank_area_loss,
    tank_temp_high_control
    )

FILES_MODEL_SPECS = DIRECTORY.FILES_MODEL_SPECS

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

        # tank
    #     self.vol = Variable(0.315,"m3")
    #     self.height = Variable(1.45, "m")  # It says 1.640 in specs, but it is external height, not internal
    #     self.height_inlet = Variable(0.113, "m")
    #     self.height_outlet = Variable(1.317, "m")
    #     self.height_heater = Variable(0.103, "m")
    #     self.height_thermostat = Variable(0.103, "m")
    #     self.U = Variable(0.9, "W/m2-K")

    #     #numerical simulation
    #     self.fluid = Water()
    #     self.nodes = 10     # Tank nodes. DO NOT CHANGE, unless TRNSYS layout is changed too!
    #     self.temps_ini = 3  # [-] Initial temperature of the tank. Check trnsys.editing_dck_tank() for options

    #     # control
    #     self.temp_max = Variable(65.0, "degC")  #Maximum temperature in the tank
    #     self.temp_deadband = Variable(10.0, "degC") # Dead band for max temp control
    #     self.temp_min = Variable(45.0, "degC")  # Minimum temperature in the tank
    #     self.temp_consump = Variable(45.0, "degC") #Consumption temperature

    # @property
    # def tank_thermal_cap(self) -> Variable:
    #     return tank_thermal_capacity(self)
    # @property
    # def tank_diam(self) -> Variable:
    #     return tank_diameter(self)
    # @property
    # def tank_area_loss(self) -> Variable:
    #     return tank_area_loss(self)
    # @property
    # def tank_temp_high_control(self) -> Variable:
    #     return tank_temp_high_control(self)


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