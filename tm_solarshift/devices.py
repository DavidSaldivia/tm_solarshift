import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Any, Tuple

# CONV = {
#     "MJ_to_kWh": 1000/3600.,
#     "J_to_kWh": 1./(1000*3600.),
#     "W_to_kJh": 3.6,
#     "min_to_s": 60.,
#     "min_to_hr": 1/60.,
#     "hr_to_s": 3600.,
#     "L_to_m3": 1e-3,
#     "W_to_MJ/hr": 3.6e-3
# }

UNIT_CONV = {
    "length" : {
        "m": 1e0,
        "mm": 1e3,
        "km": 1e-3,
        "mi": 1e0/1609.34,
        "ft": 3.28084,
        "in": 39.3701,
        },
    "area" : {
        "m2": 1e0,
        "mm2": 1e6,
        "km2": 1e-6,
        "ha": 1e-4,
    },
    "volume": {
        "m3": 1e0,
        "L": 1e3,
        },
    "time": {
        "s": 1e0,
        "min": 1e0/60,
        "h": 1e0/3600, "hr": 1e0/3600,
        "d": 1e0/(24*3600), "day": 1e0/(24*3600),
        "wk": 1e0/(24*3600*7),
        "mo": 1e0/(24*3600*30),
        "yr": 1e0/(24*3600*365),
    },
    "mass": {
        "kg": 1e0,
        "g": 1e3,
        "ton": 1e-3,
        "lb": 2.20462,
        "oz": 35.274,
    },
    "mass_flowrate": {
        "kg/s": 1e0,
        "g/s": 1e3,
        "kg/hr": 3600,
    },
    "energy": {
        "J": 1e0,
        "kJ": 1e-3,
        "MJ": 1e-6,
        "Wh": 1e-3/3.6,
        "kWh": 1e-6/3.6,
        "cal": 4.184,
        "kcal": 4184,
    },
    "power": {
        "W": 1e0,
        "kW": 1e-3,
        "MW": 1e-6,
        "J/h": 3.6e6, "J/hr": 3.6e6,
        "kJ/h": 3.6e0, "kJ/hr": 3.6e0,
        "MJ/h": 3.6e-3, "MJ/hr": 3.6e-3,
    },
    "pressure": {
        "Pa": 1e0,
        "bar": 1e-5,
        "psi": 1e0/6894.76,
        "atm": 1e0/101300,
    },
    "velocity": {
        "m/s": 1e0,
        "km/hr": 3.6,
        "mi/hr": 2.23694,
        "ft/s": 3.28084,
    },
    "angular": {
        "rad": 1e0,
        "deg": 180./np.pi,
    },
#-------------------
    "density": {
        "kg/m3": 1e0,
        "g/cm3": 1e-3,
    },
    "specific_heat": {
        "J/kgK": 1e0, "J/kg-K": 1e0,
        "kJ/kgK": 1e-3, "kJ/kg-K": 1e-3,
    }
}

# UNIT_TYPES = {}
# for type_unit in UNIT_CONV:
#     for unit in UNIT_CONV[type_unit]:
#         UNIT_TYPES[unit] = type_unit

UNIT_TYPES = {unit:type_unit for type_unit in UNIT_CONV for unit in UNIT_CONV[type_unit]}

#-------------------------
def conversion_factor(unit1: str, unit2: str) -> float:
    if UNIT_TYPES[unit1] == UNIT_TYPES[unit2]:
        type_unit = UNIT_TYPES[unit1]
        conv_factor = UNIT_CONV[type_unit][unit2] / UNIT_CONV[type_unit][unit1]
    else:
        raise ValueError(f"Units {unit1} and {unit2} do not represent the same physical quantity.")
    return conv_factor

#-------------------------
#Utilities classes
class Variable():
    def __init__(self, value: float, unit: str = None, type="scalar"):
        self.value = value
        self.unit = unit
        self.type = type

    def get_value(self, unit: str = None):
        
        if unit == None:
            unit = self.unit

        if self.unit == unit:
            return self.value
        
        if UNIT_TYPES[unit] == UNIT_TYPES[self.unit]:
            conv_factor = conversion_factor(self.unit, unit)
            return self.value * conv_factor
        
        if self.unit != unit: #Check units
            raise ValueError(
                f"It is not possible to convert Variable (in {self.unit}) to the specified unit {unit}."
                )

    def __repr__(self) -> str:
        return f"{self.value:} [{self.unit}]"

#-------------------------
class VariableList():
    def __init__(self, values: List, unit: str = None, type="scalar"):
        self.values = values
        self.unit = unit
        self.type = type

    def get_values(self, unit=None):
        values = self.values
        if self.unit != unit: #Check units
            raise ValueError(
                f"The variable used have different units: {unit} and {self.unit}"
                )
        return values

    def __repr__(self) -> str:
        return f"{self.values:} [{self.unit}]"


#-------------------------
class Water():
    def __init__(self):
        self.rho = Variable(1000., "kg/m3")  # density (water)
        self.cp = Variable(4180., "J/kg-K")  # specific heat (water)
        self.k = Variable(0.6, "W/m-K")  # thermal conductivity (water)
    def __repr__(self) -> str:
        return "water"

#-------------------------
#Solar System and auxiliary devices
class SolarSystem():
    def __init__(self):
        self.nom_power = Variable(4000.0,"W")

#-------------------------
#List of heater devices        
class ResistiveSingle():
    def __init__(self, **kwargs):

        #Loading all default values
        # heater
        self.nom_power = Variable(3600.0, "W")
        self.eta = Variable(1.0, "-")
        
        # tank
        self.vol = Variable(0.315,"m3")
        self.height = Variable(1.640, "m")
        self.height_inlet = Variable(0.113, "m")
        self.height_outlet = Variable(0.1317, "m")
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
    def from_model_file(cls, file_path: str = "", model:str = ""):
        
        if file_path=="":
            from tm_solarshift.general import DATA_DIR
            import os
            file_path = os.path.join(DATA_DIR["specs"], "data_models_RS.csv")
        file_data = pd.read_csv(file_path, index_col=0)
        specs = file_data.loc[model]
        units = file_data.loc["units"]
        
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
            self.height = Variable(1.640, "m")
            self.height_inlet = Variable(0.113, "m")
            self.height_outlet = Variable(0.1317, "m")
            self.height_heater = Variable(0.103, "m")
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


#-------------------------
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

#-------------------------
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
        STEP_h: float = 3/60.
) -> dict:

    MJ_TO_kWh = conversion_factor("MJ", "kWh")
    min_TO_sec = conversion_factor("min", "s")
    min_TO_hr = conversion_factor("min", "hr")
    L_TO_m3 = conversion_factor("L", "m3")
    W_TO_MJ_hr = conversion_factor("W", "MJ/hr")
    kg_TO_ton = conversion_factor("kg", "ton")

    if type(HW_flow) == list:
        HW_flow = np.array(HW_flow)

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

    annual_energy = E_HWD.sum()                         #[kWh]
    emissions = E_HWD * specific_emissions * kg_TO_ton  #[tonCO2]
    annual_emissions = emissions.sum()                  #[tonCO2_annual]

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

#-----------------------
if __name__ == "__main__":

    print(conversion_factor("W", "kJ/hr"))

    time_sim = Variable(365, "d")
    print(f"time_sim in days: {time_sim.get_value("d")}")
    print(f"time_sim in hours: {time_sim.get_value("hr")}")
    print(f"time_sim in seconds: {time_sim.get_value("s")}")

    heater = ResistiveSingle.from_model_file(model="491315")
    pass
#-------------------------
def main():
    heater = HeatPump()
    print(heater.thermal_cap)
    print(heater.diam)
    print(heater.area_loss)
    print(heater.temp_high_control)

    heater = GasHeaterInstantaneous()
    output = heater.run_simple_thermal_model([200,100])
    print(output)

    return

#-------------------------
if __name__=="__main__":
    main()
