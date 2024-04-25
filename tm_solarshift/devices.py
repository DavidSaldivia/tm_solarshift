import os
import numpy as np
import pandas as pd
from tm_solarshift.constants import DIRECTORY
from tm_solarshift.utils.units import (
    Variable,
    Water,
    conversion_factor as CF
)

FILE_MODELS_RS = os.path.join(DIRECTORY.DIR_DATA["specs"], "data_models_RS.csv")
FILE_MODELS_HP = os.path.join(DIRECTORY.DIR_DATA["specs"], "data_models_HP.csv")
FILE_MODELS_GI = os.path.join(DIRECTORY.DIR_DATA["specs"], "data_models_GI.csv")
FILE_MODELS_GS = os.path.join(DIRECTORY.DIR_DATA["specs"], "data_models_GS.csv")
FILE_MODELS_TH = os.path.join(DIRECTORY.DIR_DATA["specs"], "data_models_TH.csv")

#-------------------------
#Solar System and auxiliary devices
class SolarSystem():
    def __init__(self):

        self.nom_power = Variable(4000.0,"W")
        self.lat = Variable(-33.86,"-")
        self.lon = Variable(151.22,"-")
        self.tilt = Variable(abs(self.lat.get_value("-")),"-")
        self.orient = Variable(180.0,"-")

        self.model = "-"
        self.cost = Variable(np.nan, "AUD")

        self.profile_PV = 1

    def load_PV_generation(
            self,
            df: pd.DataFrame,
            tz: str = 'Australia/Brisbane',
            unit: str = "kW",
    ) -> pd.DataFrame:
    
        from tm_solarshift.external.pvlib_utils import (get_PV_generation, load_trnsys_weather)

        df_sample = load_trnsys_weather()  #Fix this!
        df_aux = get_PV_generation(tz=tz,
                                   df = df_sample,
                                   latitude = self.lat.get_value("-"),
                                   longitude = self.lon.get_value("-"),
                                   tilt = self.tilt.get_value("-"),
                                   orient = self.orient.get_value("-"),
                                   PV_nompower = self.nom_power.get_value("W"),)
    
        df_aux.index = df.index
        PVPower =  df_aux["PVPower"] * CF("W", unit)
        return PVPower
    
#-------------------------
#List of heater devices        
class ResistiveSingle():
    def __init__(self):

        #Loading all default values
        # heater
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
        self.temps_ini = 3  # [-] Initial temperature of the tank. Check trnsys.editing_dck_tank() for options
        self.fluid = Water()

        # control
        self.temp_max = Variable(65.0, "degC")  #Maximum temperature in the tank
        self.temp_deadband = Variable(10.0, "degC") # Dead band for max temp control
        self.temp_min = Variable(45.0, "degC")  # Minimum temperature in the tank
        self.temp_consump = Variable(45.0, "degC") #Consumption temperature

        #finance
        self.cost = Variable(np.nan, "AUD")
        self.model = "-"

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
        file_path: str = FILE_MODELS_RS,
        model:str = "",
        ):
        
        df = pd.read_csv(file_path, index_col=0)
        specs = df.loc[model]
        units = df.loc["units"]
        
        output = cls()
        for (lbl,value) in specs.items():
            unit = units[lbl]
            try:
                value = float(value)
            except:
                pass          
            setattr(output, lbl, Variable(value, unit) )

        return output

#-------------------------
class HeatPump():
    def __init__(self):
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

        #finance
        self.cost = Variable(np.nan, "AUD")
        self.model = "-"
        
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
        file_path: str = FILE_MODELS_HP,
        model:str = "",
        ):
        
        df = pd.read_csv(file_path, index_col=0)
        specs = df.loc[model]
        units = df.loc["units"]
        
        output = cls()
        for (lbl,value) in specs.items():
            unit = units[lbl]
            try:
                value = float(value)
            except:
                pass          
            setattr(output, lbl, Variable(value, unit) )

        return output


#-------------------------
class GasHeaterInstantaneous():
    def __init__(self):
        # Default data from:
        # https://www.rheem.com.au/rheem/products/Residential/Gas-Continuous-Flow/Continuous-Flow-%2812---27L%29/Rheem-12L-Gas-Continuous-Flow-Water-Heater-%3A-50%C2%B0C-preset/p/876812PF#collapse-1-2-1
        # Data from model Rheim 20
        #heater
        self.nom_power = Variable(157., "MJ/hr")
        self.flow_water = Variable(20., "L/min")
        self.deltaT_rise = Variable(25., "dgrC")
        self.heat_value = Variable(47.,"MJ/kg_gas")
        
        #tank
        self.vol = Variable(0., "m3")
        self.thermal_cap = Variable(0., "kWh")
        self.fluid = Water()

        #control
        self.temp_consump = Variable(45.0, "degC")

        #finance
        self.cost = Variable(np.nan, "AUD")
        self.model = "-"

    @property
    def eta(self) -> Variable:
        
        nom_power = self.nom_power.get_value("MJ/hr")
        deltaT_rise = self.deltaT_rise.get_value("dgrC")
        flow_w = self.flow_water.get_value("m3/s")
        cp_w = self.fluid.cp.get_value("J/kg-K")
        rho_w = self.fluid.rho.get_value("kg/m3")
        
        HW_energy = (flow_w * rho_w * cp_w) * deltaT_rise * CF("W", "MJ/hr")  #[MJ/hr]
        return Variable(HW_energy / nom_power, "-")

    @classmethod
    def from_model_file(
        cls,
        file_path: str = FILE_MODELS_GI,
        model:str = "",
        ):
        
        df = pd.read_csv(file_path, index_col=0)
        specs = df.loc[model]
        units = df.loc["units"]
        
        output = cls()
        for (lbl,value) in specs.items():
            unit = units[lbl]
            try:
                value = float(value)
            except:
                pass          
            setattr(output, lbl, Variable(value, unit) )
        return output

#-------------------------
class GasHeaterStorage():
    def __init__(self):

        # Gas heater data are from GasInstantaneous:
        # https://www.rheem.com.au/rheem/products/Residential/Gas-Continuous-Flow/Continuous-Flow-%2812---27L%29/Rheem-12L-Gas-Continuous-Flow-Water-Heater-%3A-50%C2%B0C-preset/p/876812PF#collapse-1-2-1
        # Data from model Rheim 20

        # Tank data are from ResistiveSingle default

        #heater
        self.nom_power = Variable(157., "MJ/hr")
        self.flow_water = Variable(20., "L/min")
        self.deltaT_rise = Variable(25., "dgrC")
        self.heat_value = Variable(47.,"MJ/kg_gas")

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

        #finance
        self.cost = Variable(np.nan, "AUD")
        self.model = "-"

    @property
    def eta(self) -> Variable:
        
        nom_power = self.nom_power.get_value("MJ/hr")
        deltaT_rise = self.deltaT_rise.get_value("dgrC")
        flow_w = self.flow_water.get_value("m3/s")
        cp_w = self.fluid.cp.get_value("J/kg-K")
        rho_w = self.fluid.rho.get_value("kg/m3")

        HW_energy = (flow_w * rho_w * cp_w) * deltaT_rise * CF("W", "MJ/hr")  #[MJ/hr]
        return Variable(HW_energy / nom_power, "-")
    
    @classmethod
    def from_model_file(
        cls,
        file_path: str = FILE_MODELS_GS,
        model:str = "",
        ):
        
        df = pd.read_csv(file_path, index_col=0)
        specs = df.loc[model]
        units = df.loc["units"]
        
        output = cls()
        for (lbl,value) in specs.items():
            unit = units[lbl]
            try:
                value = float(value)
            except:
                pass          
            setattr(output, lbl, Variable(value, unit) )
        return output
    
    @property
    def thermal_cap(self):
        return tank_thermal_capacity(self)
    @property
    def diam(self):
        return tank_diameter(self)
    @property
    def area_loss(self):
        return tank_area_loss(self)

#-------------------
class SolarThermalElecAuxiliary():
    def __init__(self):

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

        # Auxiliary resistive heater
        self.nom_power = Variable(3600.0, "W")
        self.eta = Variable(1.0, "-")

        #finance
        self.cost = Variable(np.nan, "AUD")
        self.model = "-"

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
        file_path: str = FILE_MODELS_TH,
        model:str = "",
        ):
        
        df = pd.read_csv(file_path, index_col=0)
        specs = df.loc[model]
        units = df.loc["units"]
        
        output = cls()
        for (lbl,value) in specs.items():
            unit = units[lbl]
            try:
                value = float(value)
            except:
                pass          
            setattr(output, lbl, Variable(value, unit) )

        return output

#-------------------------
def tank_thermal_capacity(
        tank: ResistiveSingle | HeatPump | GasHeaterStorage | SolarThermalElecAuxiliary
) -> Variable:
    vol = tank.vol.get_value("m3")
    rho = tank.fluid.rho.get_value("kg/m3")
    cp = tank.fluid.cp.get_value("J/kg-K")
    temp_max = tank.temp_max.get_value("degC")
    temp_min = tank.temp_min.get_value("degC")
    thermal_cap = vol * (rho * cp) * (temp_max - temp_min) / 3.6e6
    return Variable( thermal_cap, "kWh")

def tank_diameter(
        tank: ResistiveSingle | HeatPump | GasHeaterStorage | SolarThermalElecAuxiliary
) -> Variable:
    vol = tank.vol.get_value("m3")
    height = tank.height.get_value("m")
    diam = (4 * vol / np.pi / height) ** 0.5
    return Variable( diam , "m" )

def tank_area_loss(
        tank: ResistiveSingle | HeatPump | GasHeaterStorage | SolarThermalElecAuxiliary
) -> Variable:
    diam = tank.diam.get_value("m")
    height = tank.height.get_value("m")
    area_loss = np.pi * diam * (diam / 2 + height)
    return Variable( area_loss, "m2" ) 

def tank_temp_high_control(
        tank: ResistiveSingle | HeatPump | GasHeaterStorage | SolarThermalElecAuxiliary
) -> Variable:
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
