from __future__ import annotations
import numpy as np
import pandas as pd
from typing import TYPE_CHECKING, TypeAlias

from tm_solarshift.constants import DIRECTORY
from tm_solarshift.utils.units import (Variable, Water)
from tm_solarshift.models.gas_heater import GasHeaterStorage
from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary

FILES_MODEL_SPECS = DIRECTORY.FILES_MODEL_SPECS

#-------------------------
#List of heater devices        
class ResistiveSingle():
    def __init__(self):

        # description
        self.name = "Conventional resistive immersive heater (single unit)."
        self.label = "resistive"
        self.model = "-"
        self.cost = Variable(np.nan, "AUD")

        #Loading all default values
        # heater data
        self.nom_power = Variable(3600.0, "W")
        self.eta = Variable(1.0, "-")
        
        # tank geometry and losses
        self.vol = Variable(0.315,"m3")
        self.height = Variable(1.45, "m")  # It says 1.640 in specs, but it is external height, not internal
        self.height_inlet = Variable(0.113, "m")
        self.height_outlet = Variable(1.317, "m")
        self.height_heater = Variable(0.103, "m")
        self.height_thermostat = Variable(0.103, "m")
        self.U = Variable(0.9, "W/m2-K")

        #numerical simulation
        self.fluid = Water()
        self.nodes = 10     # Tank nodes. DO NOT CHANGE, unless TRNSYS layout is changed too!
        self.temps_ini = 3  # [-] Initial temperature of the tank. Check trnsys.editing_dck_tank() for options

        # control
        self.temp_max = Variable(65.0, "degC")  #Maximum temperature in the tank
        self.temp_deadband = Variable(10.0, "degC") # Dead band for max temp control
        self.temp_min = Variable(45.0, "degC")  # Minimum temperature in the tank
        self.temp_consump = Variable(45.0, "degC") #Consumption temperature

    def __eq__(self, other) : 
            return self.__dict__ == other.__dict__
    
    @property
    def thermal_cap(self):
        return tank_thermal_capacity(self)
    @property
    def diam(self):
        return tank_diameter(self)
    @property
    def area_loss(self):
        return tank_area_loss(self)
    @property
    def temp_high_control(self):
        return tank_temp_high_control(self)

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
        for (lbl,value) in specs.items():
            unit = units[lbl]
            try:
                value = float(value)
            except:
                pass          
            setattr(output, lbl, Variable(value, unit) )

        return output
    
    def run_thermal_model(
            self,
            ts: pd.DataFrame,
            verbose: bool = False,
    ) -> pd.DataFrame:
        from tm_solarshift.models.trnsys import TrnsysDEWH
        trnsys_dewh = TrnsysDEWH(DEWH=self, ts=ts)
        df_tm = trnsys_dewh.run_simulation(ts, verbose=verbose)
        return df_tm

#-------------------------
class HeatPump():
    def __init__(self):

        # description
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
        return tank_thermal_capacity(self)
    @property
    def diam(self):
        return tank_diameter(self)
    @property
    def area_loss(self):
        return tank_area_loss(self)

    @classmethod
    def from_model_file(
        cls,
        file_path: str = FILES_MODEL_SPECS["heat_pump"],
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
    
    def run_thermal_model(
            self,
            ts: pd.DataFrame,
            verbose: bool = False,
    ) -> pd.DataFrame:
        from tm_solarshift.models.trnsys import TrnsysDEWH
        trnsys_dewh = TrnsysDEWH(DEWH=self, ts=ts)
        df_tm = trnsys_dewh.run_simulation(ts, verbose=verbose)
        return df_tm

#------------------
HeaterWithTank: TypeAlias = ResistiveSingle | HeatPump | GasHeaterStorage | SolarThermalElecAuxiliary
def tank_thermal_capacity(tank: HeaterWithTank) -> Variable:
    vol = tank.vol.get_value("m3")
    rho = tank.fluid.rho.get_value("kg/m3")
    cp = tank.fluid.cp.get_value("J/kg-K")
    temp_max = tank.temp_max.get_value("degC")
    temp_min = tank.temp_min.get_value("degC")
    thermal_cap = vol * (rho * cp) * (temp_max - temp_min) / 3.6e6
    return Variable( thermal_cap, "kWh")

def tank_diameter(tank: HeaterWithTank) -> Variable:
    vol = tank.vol.get_value("m3")
    height = tank.height.get_value("m")
    diam = (4 * vol / np.pi / height) ** 0.5
    return Variable( diam , "m" )

def tank_area_loss(tank: HeaterWithTank) -> Variable:
    diam = tank.diam.get_value("m")
    height = tank.height.get_value("m")
    area_loss = np.pi * diam * (diam / 2 + height)
    return Variable( area_loss, "m2" ) 

def tank_temp_high_control(tank: HeaterWithTank) -> Variable:
    temp_max = tank.temp_max.get_value("degC")
    temp_deadband = tank.temp_deadband.get_value("degC")
    temp_high_control = temp_max - temp_deadband / 2.0
    return Variable(temp_high_control, "degC")

#-------------------------
def main():
    #Example to load ResistiveSingle defining the model (it reads a csv file with data)
    heater = ResistiveSingle.from_model_file(model="491315")
    print(heater.thermal_cap)
    print(heater.diam)
    print(heater.area_loss)
    print(heater.temp_high_control)
    print()

    #Example of Heat Pump technical information
    heater = HeatPump()
    print(heater.thermal_cap)
    print(heater.diam)
    print(heater.area_loss)
    print(heater.temp_high_control)
    print()

    #Example of Gas Heater Instantenous
    from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)
    heater = GasHeaterInstantaneous()
    print(heater.nom_power)
    print(heater.eta)
    print(heater.vol)
    print()

    #Example of Gas Heater Instantenous
    heater = GasHeaterStorage()
    print(heater.nom_power)
    print(heater.eta)
    print(heater.vol)

    return

#-------------------------
if __name__=="__main__":
    main()
