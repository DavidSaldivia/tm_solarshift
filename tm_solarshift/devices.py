import numpy as np
from typing import Optional, List, Dict, Any, Tuple
# from tm_solarshift.general import CONV

CONV = {
    "MJ_to_kWh": 1000/3600.,
    "W_to_kJh": 3.6,
    "min_to_s": 60.,
    "min_to_hr": 1/60.,
    "L_to_m3": 1e-3,
    "W_to_MJ/hr": 3.6e-3
}

#Utilities classes
class Variable():
    def __init__(self, value: float, unit: str = None, type="scalar"):
        self.value = value
        self.unit = unit
        self.type = type

    def get_value(self, unit=None):
        value = self.value
        if self.unit != unit: #Check units
            raise ValueError(
                f"The variable used have different units: {unit} and {self.unit}"
                )
        return value

    def __repr__(self) -> str:
        return f"{self.value:} [{self.unit}]"

class Water():
    def __init__(self):
        self.rho = Variable(1000., "kg/m3")  # density (water)
        self.cp = Variable(4180., "J/kg-K")  # specific heat (water)
        self.k = Variable(0.6, "W/m-K")  # thermal conductivity (water)

#Solar System and auxiliary devices
class SolarSystem():
    def __init__(self):
        self.nom_power = Variable(4000.0,"W")

#List of heater devices        
class ResistiveSingle():
    def __init__(self, source: str="default"):

        if source == "default":
            # heater
            self.nom_power = Variable(3600.0, "W")
            self.eta = Variable(1.0, "-")
            
            # tank
            self.vol = Variable(0.315,"m3")
            self.height = Variable(1.3, "m")
            self.U = Variable(0.9, "W/m2-K")
            self.nodes = 10     # Tank nodes. DO NOT CHANGE, unless TRNSYS layout is changed too!
            self.temps_ini = 3  # [-] Initial temperature of the tank. Check Editing_dck_tank() below for the options
            self.fluid = Water()

            # control
            self.temp_max = Variable(65.0, "degC")  #Maximum temperature in the tank
            self.temp_deadband = Variable(10.0, "degC") # Dead band for max temp control
            self.temp_min = Variable(45.0, "degC")  # Minimum temperature in the tank
            self.temp_consump = Variable(45.0, "degC") #Consumption temperature

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


class HeatPump():
    def __init__(self, source: str="default"):

        if source == "default":
            # heater
            self.nom_power_th = Variable(5240.0, "W")
            self.nom_power_el = Variable(870.0, "W")
            self.eta = Variable(6.02, "-")
            self.nom_tamb = Variable(32.6, "degC")
            self.nom_tw = Variable(21.1, "degC")

            # tank
            self.vol = Variable(0.315,"m3")
            self.height = Variable(1.3, "m")
            self.U = Variable(0.9, "W/m2-K")
            self.nodes = 10     # Tank nodes. DO NOT CHANGE, unless TRNSYS layout is changed too!
            self.temps_ini = 3  # [-] Initial temperature of the tank. Check Editing_dck_tank() below for the options
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


def tank_thermal_capacity(tank):
    vol = tank.vol.get_value("m3")
    rho = tank.fluid.rho.get_value("kg/m3")
    cp = tank.fluid.cp.get_value("J/kg-K")
    temp_max = tank.temp_max.get_value("degC")
    temp_min = tank.temp_min.get_value("degC")
    thermal_cap = vol * (rho * cp) * (temp_max - temp_min) / 3.6e6
    return Variable( thermal_cap, "kWh")

def tank_diameter(tank):
    vol = tank.vol.get_value("m3")
    height = tank.height.get_value("m")
    diam = (4 * vol / np.pi / height) ** 0.5
    return Variable( diam , "m" )

def tank_area_loss(tank):
    diam = tank.diam.get_value("m")
    height = tank.height.get_value("m")
    area_loss = np.pi * diam * (diam / 2 + height)
    return Variable( area_loss, "m2" ) 

def tank_temp_high_control(tank):
    temp_max = tank.temp_max.get_value("degC")
    temp_deadband = tank.temp_deadband.get_value("degC")
    temp_high_control = temp_max - temp_deadband / 2.0
    return Variable(temp_high_control, "degC")

class GasHeaterInstantaneous():
    def __init__(self, source: str="default"):
        if source == 'default':
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
            self.fluid = Water()

            #control
            self.temp_consump = Variable(45.0, "degC")

        self.fluid = Water()

    def run_simple_thermal_model(self, HW_flow: List = [200.,]):
        return tm_heater_gas_instantaneuos(self, HW_flow) 


def tm_heater_gas_instantaneuos(
        heater: Any = GasHeaterInstantaneous(),
        HW_flow: List = [200.,],
) -> dict:

    STEP_h = 3/60. #Replace it for a constant later

    MJ_TO_kWh = CONV["MJ_to_kWh"]
    min_TO_sec = CONV["min_to_s"]
    min_TO_hr = CONV["min_to_hr"]
    L_TO_m3 = CONV["L_to_m3"]
    W_TO_MJ_hr = CONV["W_to_MJ/hr"]
    kgCO2_TO_kgCH4 = 44. / 16.

    nom_power = heater.nom_power.get_value("MJ/hr")
    deltaT_rise = heater.deltaT_rise.get_value("dgrC")
    flow_water = heater.flow_water.get_value("L/min")

    #Assuming pure methane for gas
    heat_value = heater.heat_value.get_value("MJ/kg_gas")
            

    cp_water = heater.fluid.cp.get_value("J/kg-K")
    rho_water = heater.fluid.rho.get_value("kg/m3")

    #Calculations
    flow_gas = nom_power / heat_value         #[kg/hr]
    HW_energy = ((flow_water / min_TO_sec * L_TO_m3)
                 * rho_water * cp_water 
                 * deltaT_rise
                 * W_TO_MJ_hr
                 )  #[MJ/hr]

    eta = HW_energy / nom_power #[-]
    specific_energy = (nom_power / flow_water
                       * min_TO_hr * MJ_TO_kWh) #[kWh/L]

    specific_emissions = (kgCO2_TO_kgCH4 
                     / (heat_value * MJ_TO_kWh)
                     / eta
                    ) #[kg_CO2/kWh_thermal]

    E_HWD = specific_energy * HW_flow * STEP_h   #[kWh]

    annual_energy = E_HWD.sum()                  #[kWh]
    emissions = E_HWD * specific_emissions/1000. #[tonCO2]
    annual_emissions = emissions.sum()           #[tonCO2_annual]

    output = {
        "flow_gas" : flow_gas,
        "HW_energy" : HW_energy,
        "eta" : eta,
        "specific_energy" : specific_energy,
        "specific_emissions" : specific_emissions,
        "annual_energy" : annual_energy,
        "annual_emissions": annual_emissions,
        "E_HWD" : E_HWD,
        "emissions" : emissions,
    }
    return output


def main():
    heater = HeatPump()

    print(heater.thermal_cap)
    print(heater.diam)
    print(heater.area_loss)
    print(heater.temp_high_control)

    return

if __name__=="__main__":
    main()
