import numpy as np

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

        self.derived_parameters()

    def derived_parameters(self):
        derived_parameter_tank(self)
        return


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
        self.derived_parameters()
        
    def derived_parameters(self):
        derived_parameter_tank(self)
        return

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
            self.vol = 0.
            self.fluid = Water()

            #control
            self.temp_consump = Variable(45.0, "degC")

        self.fluid = Water()


def derived_parameter_tank(self):
    rho = self.fluid.rho.get_value("kg/m3")
    cp = self.fluid.cp.get_value("J/kg-K")
    vol = self.vol.get_value("m3")
    temp_max = self.temp_max.get_value("degC")
    temp_min = self.temp_min.get_value("degC")
    temp_deadband = self.temp_deadband.get_value("degC")
    height = self.height.get_value("m")

    self.thermal_cap = Variable(
        vol * (rho * cp) * (temp_max - temp_min) / 3.6e6,
        "kWh",
        )
    self.diam = Variable(
        (4 * vol / np.pi / height) ** 0.5,
        "m",
        )
    diam = self.diam.get_value("m")
    self.area_loss = Variable(
        np.pi * diam * (diam / 2 + height),
        "m2",
        ) 

    self.temp_high_control = Variable(
        temp_max - temp_deadband / 2.0,
        "degC",
        )
    return
