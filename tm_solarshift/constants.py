import os
import numpy as np

class DIRECTORY():
    #Repository structure
    DIR_MAIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DIR_FILE = os.path.dirname(os.path.abspath(__file__))
    DIR_DATA = {
        "weather" : os.path.join(DIR_MAIN, "data", "weather"),
        "HWDP" : os.path.join(DIR_MAIN, "data", "HWD_Profiles"),
        "tariffs" : os.path.join(DIR_MAIN, "data", "energy_plans"),
        "energy_market": os.path.join(DIR_MAIN, "data", "energy_market"),
        "emissions" : os.path.join(DIR_MAIN, "data", "emissions"),
        "samples" : os.path.join(DIR_MAIN, "data", "samples"),
        "layouts" : os.path.join(DIR_MAIN, "data", "trnsys_layouts"),
        "specs" : os.path.join(DIR_MAIN, "data", "device_specs"),
        "SA_processed" : os.path.join(DIR_MAIN, "data", "SA_processed"),
        }
    DIR_RESULTS = os.path.join(DIR_MAIN, "results")
    FILE_SAMPLES ={
        "HWD_daily" : os.path.join(DIR_DATA["samples"], "HWD_Daily_Sample_site.csv"),
        "HWD_events": os.path.join(DIR_DATA["samples"], "HWD_events.xlsx"),
        }

# General definitions
class DEFINITIONS():
    SEASON = {
        "summer": [12, 1, 2],
        "autumn": [3, 4, 5],
        "winter": [6, 7, 8],
        "spring": [9, 10, 11],
    }
    DAYOFWEEK = {
        "weekday": [0, 1, 2, 3, 4],
        "weekend": [5, 6]
    }
    CLIMATE_ZONE = {
        1: "Hot humid summer",
        2: "Warm humid summer",
        3: "Hot dry summer, mild winter",
        4: "Hot dry summer, cold winter",
        5: "Warm summer, cool winter",
        6: "Mild warm summer, cold winter",
    }
    LOCATIONS_NEM_REGION = {
        "Sydney": "NSW1",
        "Melbourne": "VIC1",
        "Brisbane": "QLD1",
        "Adelaide": "SA1",
        "Canberra": "NSW1",
        "Townsville": "QLD1",
    }
    HWDP_NAMES = {
        1:'Mor & Eve Only',
        2:'Mor & Eve w daytime',
        3:'Evenly',
        4:'Morning',
        5:'Evening',
        6:'late Night'
    }
    CL_NAMES = {
        0:'GS',
        1:'CL1',
        2:'CL2',
        3:'CL3',
        4:'SS'
    }

# Profiles
class PROFILES():
    TYPES = {
        "HWDP": ["P_HWD", "m_HWD", "Events", "m_HWD_day"],
        "weather": ["GHI", "Temp_Amb", "Temp_Mains"],
        "control": ["CS"],
        "electric": ["PV_Gen", "Import_Grid", "Import_CL"],
        "economic": ["Tariff", "Wholesale_Market"],
        "emissions": ["Intensity_Index", "Marginal_Emission"],
    }
    COLUMNS = [
        item for sublist in 
            [value for _, value in TYPES.items()]
        for item in sublist
    ]

# Unit conversion factors
class UNITS():
    CONVERSIONS = {
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

    TYPES = dict()
    for type_unit in CONVERSIONS.keys():
        for unit in CONVERSIONS[type_unit].keys():
            TYPES[unit] = type_unit


    #-------------------------
    @classmethod
    def conversion_factor(cls, unit1: str, unit2: str) -> float:
        """ Function to obtain conversion factor between units.
        The units must be in the UNIT_CONV dictionary.
        If they are units from different phyisical quantities an error is raised.
        """
        if cls.TYPES[unit1] == cls.TYPES[unit2]:
            type_unit = cls.TYPES[unit1]
            conv_factor = cls.CONVERSIONS[type_unit][unit2] / cls.CONVERSIONS[type_unit][unit1]
        else:
            raise ValueError(f"Units {unit1} and {unit2} do not represent the same physical quantity.")
        return conv_factor


def main():

    print(UNITS.conversion_factor("W","kJ/hr"))
    return

if __name__=="__main__":
    main()
    pass
