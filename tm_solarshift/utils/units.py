import numpy as np

#-------------------------
# Unit conversion factors
CONVERSIONS = {
    "adim" : {
        "-": 1e0,
        None: 1e0,
        "": 1e0,
        " ": 1e0,
    },
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
        "wk": 1e0/(24*3600*7), "week": 1e0/(24*3600*7),
        "mo": 1e0/(24*3600*30), "month": 1e0/(24*3600*30),
        "yr": 1e0/(24*3600*365), "year": 1e0/(24*3600*365),
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
        "kg/min": 60,
        "kg/hr": 3600,
    },
    "volume_flowrate": {
        "L/s": 1e0,
        "m3/s": 1e-3,
        "m3/min": 1e-3*60,
        "m3/hr": 1e-3*3600,
        "L/min": 60,
        "L/hr": 3600,
        "ml/s": 1e3,
    },
    "energy": {
        "J": 1e0,
        "kJ": 1e-3,
        "MJ": 1e-6,
        "Wh": 1e-3/3.6,
        "kWh": 1e-6/3.6,
        "cal": 4.184e0,
        "kcal": 4.184e3,
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
    "cost" : {
        "AUD": 1e0,
        "USD": 1.4e0,
    },
#-------------------
    "density": {
        "kg/m3": 1e0,
        "g/cm3": 1e-3,
    },
    "specific_heat": {
        "J/kgK": 1e0, "J/kg-K": 1e0,
        "kJ/kgK": 1e-3, "kJ/kg-K": 1e-3,
    },
}

UNIT_TYPES = dict()
for type_unit in CONVERSIONS.keys():
    for unit in CONVERSIONS[type_unit].keys():
        UNIT_TYPES[unit] = type_unit

#-------------------------
def conversion_factor(unit1: str, unit2: str) -> float:
    """ Function to obtain conversion factor between units.
    The units must be in the UNIT_CONV dictionary.
    If they are units from different phyisical quantities an error is raised.
    """
    if UNIT_TYPES[unit1] == UNIT_TYPES[unit2]:
        type_unit = UNIT_TYPES[unit1]
        conv_factor = CONVERSIONS[type_unit][unit2] / CONVERSIONS[type_unit][unit1]
    else:
        raise ValueError(f"Units {unit1} and {unit2} do not represent the same physical quantity.")
    return conv_factor

#Utilities classes
class Variable():
    """
    Class to represent parameters and variables in the system.
    It is used to store the values with their units.
    If you have a Variable instance, always obtain the value with the get_value method.
    In this way you make sure you are getting the value with the expected unit.
    get_value internally converts unit if it is possible.
    """
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
        else:
            raise ValueError( f"Variable unit ({self.unit}) and wanted unit ({unit}) are not compatible.")

    def __repr__(self) -> str:
        return f"{self.value:} [{self.unit}]"

#-------------------------
class VariableList():
    """
    Similar to Variable() but for lists.
    """
    def __init__(self, values: list, unit: str = None, type="scalar"):
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
    

def main():

    #Examples of conversion factors and Variable usage.
    print(conversion_factor("L/min","m3/s"))
    print(conversion_factor("W","kJ/hr"))
    print(conversion_factor("W", "kJ/hr"))

    time_sim = Variable(365, "d")
    print(f"time_sim in days: {time_sim.get_value("d")}")
    print(f"time_sim in hours: {time_sim.get_value("hr")}")
    print(f"time_sim in seconds: {time_sim.get_value("s")}")
    return

if __name__=="__main__":
    main()
    pass
