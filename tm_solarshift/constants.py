import os

class DIRECTORY():
    
    #DIRS
    DIR_MAIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DIR_FILE = os.path.dirname(os.path.abspath(__file__))
    DIR_DATA = {
        "energy_market": os.path.join(DIR_MAIN, "data", "energy_market"),
        "emissions" : os.path.join(DIR_MAIN, "data", "emissions"),
        "HWDP" : os.path.join(DIR_MAIN, "data", "HWD_profiles"),
        "layouts" : os.path.join(DIR_MAIN, "data", "trnsys_layouts"),
        "location" : os.path.join(DIR_MAIN, "data", "location"),
        "SA_processed" : os.path.join(DIR_MAIN, "data", "SA_processed"),
        "samples" : os.path.join(DIR_MAIN, "data", "samples"),
        "specs" : os.path.join(DIR_MAIN, "data", "device_specs"),
        "tariffs" : os.path.join(DIR_MAIN, "data", "tariffs_json_2023-24"),
        "weather" : os.path.join(DIR_MAIN, "data", "weather"),
        }
    DIR_RESULTS = os.path.join(DIR_MAIN, "results")
    DIR_PROJECTS = os.path.join(DIR_MAIN, "projects")
    
    #FILES
    FILES_HWD_SAMPLES ={
        "HWD_daily" : os.path.join(DIR_DATA["samples"], "HWD_daily_sample_site.csv"),
        "HWD_events": os.path.join(DIR_DATA["samples"], "HWD_events.xlsx"),
        }
    FILES_SOLA = {
        "CL_INFO": os.path.join(DIR_DATA["SA_processed"], "site_controlled_load_info.csv"),
        "HW_CLASS": os.path.join(DIR_DATA["SA_processed"], "site_hot_water_classification.csv"),
        "HW_STATS": os.path.join(DIR_DATA["SA_processed"], "site_hot_water_stats.csv"),
        "POSTCODES_INFO": os.path.join(DIR_DATA["location"], "site_controlled_load_lat_lng.csv"),
    }
    FILE_WHOLESALE_PRICES = os.path.join(DIR_DATA["energy_market"], 'SP_2017-2023.csv')
    FILE_POSTCODES = os.path.join(DIR_DATA["location"], "australian_postcodes.csv") # https://www.matthewproctor.com/australian_postcodes
    FILE_MERRA2_COORDS = os.path.join(DIR_DATA["location"], "merra2_coord_states.csv")
    
class DEFAULTS():
    LOCATION = "Sydney"
    HWDP = 1
    NEM_REGION = "NSW1"

# Definitions and mappings
class DEFINITIONS():
    LOCATIONS_METEONORM = [
        'Adelaide', 'Brisbane', 'Canberra',
        'Darwin', 'Melbourne', 'Perth',
        'Sydney', 'Townsville',
    ]
    LOCATIONS_FEW = ['Sydney', 'Adelaide', 'Brisbane', 'Melbourne']
    NEM_REGIONS = [ "NSW1", "VIC1", "QLD1", "SA1", "TAS1" ]
    SIMULATION_TYPES = ["annual", "mc", "historical", "hw_only", "forecast"]
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
    LOCATIONS_COORDINATES = {
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
    WEATHER_SIMULATIONS = {
        "annual" : "tmy",
        "mc": "mc",
        "historical": "historical",
        "hw_only" : "constant_day",
        "forecast": "mc",
    }
    TS_TYPES = {
        "weather": ["GHI", "Temp_Amb", "Temp_Mains"],
        "control": ["CS"],
        "electric": ["PV_Gen", "Import_Grid", "Import_CL"],
        "HWDP": ["P_HWD", "m_HWD", "m_HWD_day"],
        "economic": ["tariff", "rate_type", "Wholesale_Market"],
        "emissions": ["Intensity_Index", "Marginal_Index"],
    }
    TS_COLUMNS_ALL = [
        item for sublist in 
            [value for _, value in TS_TYPES.items()]
        for item in sublist
    ]
    
    TARIFF_TYPES = {
        "flat": "Flat Tariff",
        "tou": "Time of Use",
        "CL" : "Controlled Load",
    }
    CONTROL_TYPES = {
        "GS": "general supply",
        "CL": "controlled load",
        "timer": "timer",
        "diverter": "diverter",
    }
    CL_NAMES = {
        0:'GS',
        1:'CL1',
        2:'CL2',
        3:'CL3',
        4:'SS',
    }
    CL_MAP = {
        0:'General Supply',
        1:'Controlled Load 1',
        2:'Controlled Load 2',
        3:'Solar Soak (Ausgrid)',
        4:'Solar Soak (only)',
    }
    LIST_DNSP = [
        "Actewagl", "Ausgrid", "Ausnet", "CitiPower", "Endeavour",
        "Essential","Energex","Ergon","Horizon","Jemena","Powercor",
        "Powerwater","SAPN","TasNetworks","Unitedenergy","Western",
    ]
    HWDP_NAMES = {
        1:'Mor & Eve Only',
        2:'Mor & Eve w daytime',
        3:'Evenly',
        4:'Morning',
        5:'Evening',
        6:'late Night',
    }
    