import os
import numpy as np

class DIRECTORY():
    #Repository structure
    DIR_MAIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DIR_FILE = os.path.dirname(os.path.abspath(__file__))
    DIR_DATA = {
        "energy_market": os.path.join(DIR_MAIN, "data", "energy_market"),
        "emissions" : os.path.join(DIR_MAIN, "data", "emissions"),
        "HWDP" : os.path.join(DIR_MAIN, "data", "HWD_Profiles"),
        "layouts" : os.path.join(DIR_MAIN, "data", "trnsys_layouts"),
        "postcodes" : os.path.join(DIR_MAIN, "data", "postcodes"),
        "SA_processed" : os.path.join(DIR_MAIN, "data", "SA_processed"),
        "samples" : os.path.join(DIR_MAIN, "data", "samples"),
        "specs" : os.path.join(DIR_MAIN, "data", "device_specs"),
        "tariffs" : os.path.join(DIR_MAIN, "data", "energy_plans"),
        "weather" : os.path.join(DIR_MAIN, "data", "weather"),
        }
    DIR_RESULTS = os.path.join(DIR_MAIN, "results")
    FILE_SAMPLES ={
        "HWD_daily" : os.path.join(DIR_DATA["samples"], "HWD_Daily_Sample_site.csv"),
        "HWD_events": os.path.join(DIR_DATA["samples"], "HWD_events.xlsx"),
        }

# General definitions
class DEFINITIONS():
    LOCATION_DEFAULT = "Sydney"
    LOCATIONS_METEONORM = ['Adelaide', 'Brisbane', 'Canberra',
                     'Darwin', 'Melbourne', 'Perth', 'Sydney', 'Townsville',]
    LOCATIONS_FEW = ['Sydney', 'Adelaide', 'Brisbane', 'Melbourne']
    NEM_REGIONS = [ "NSW1", "VIC1", "QLD1", "SA1", "TAS1" ]
    STATES = {
        "SA": "South Australia",
        "NSW": "New South Wales",
        "QLD": "Queensland",
        "TAS": "Tasmania",
        "VIC": "Victoria",
        "WA": "Western Australia",
        "ACT": "Australian Capital Territory",
        "NT": "Northern Territory",
    }
    LOCATIONS_STATE = {
        "Adelaide": "SA",
        "Brisbane": "QLD",
        "Canberra": "ACT",
        "Darwin": "NT",
        'Hobart': "TAS",
        "Melbourne": "VIC",
        "Perth": "WA",
        "Sydney": "NSW",
        "Townsville": "QLD",
    }
    CITIES_COORDINATES = {
        'Adelaide': (138.6011, -34.9289),
        'Brisbane': (153.0281, -27.4678),
        'Canberra': (149.1269, -35.2931),
        'Darwin': (130.8411, -12.4381),
        'Hobart': (147.3257, -42.8826),
        'Melbourne': (144.9631, -37.8136),
        'Perth': (115.8589, -31.9522),
        'Sydney': (151.21, -33.86),
        'Townsville': (146.817, -19.25)
    }
    LOCATIONS_NEM_REGION = {
        "Sydney": "NSW1",
        "Melbourne": "VIC1",
        "Brisbane": "QLD1",
        "Adelaide": "SA1",
        "Canberra": "NSW1",
        "Townsville": "QLD1",
    }
    SEASON = {
        "summer": [12, 1, 2],
        "autumn": [3, 4, 5],
        "winter": [6, 7, 8],
        "spring": [9, 10, 11],
    }
    MONTHS = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December"
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
    CL_MAP = {
        0:'General Supply',
        1:'Controlled Load 1',
        2:'Controlled Load 2',
        3:'Solar Soak (Ausgrid)',
        4:'Solar Soak (only)',
    }

# Profiles
class PROFILES():
    TYPES = {
        "HWDP": ["P_HWD", "m_HWD", "Events", "m_HWD_day"],
        "weather": ["GHI", "Temp_Amb", "Temp_Mains"],
        "control": ["CS"],
        "electric": ["PV_Gen", "Import_Grid", "Import_CL"],
        "economic": ["Tariff", "Wholesale_Market"],
        "emissions": ["Intensity_Index", "Marginal_Index"],
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
