import os

import json


class DIRECTORY():    
    #DIRS
    DIR_MAIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DIR_FILE = os.path.dirname(os.path.abspath(__file__))
    
    with open(os.path.join(DIR_MAIN, ".dirs"), "r") as f:
        private_dirs = json.load(f)
    DIR_DATA_EXTERNAL = private_dirs["data"]
    DIR_DATA = {
        "energy_market": os.path.join(DIR_DATA_EXTERNAL, "energy_market"),
        "emissions" : os.path.join(DIR_DATA_EXTERNAL, "emissions"),
        "HWDP" : os.path.join(DIR_DATA_EXTERNAL, "HWD_profiles"),
        "layouts" : os.path.join(DIR_DATA_EXTERNAL, "trnsys_layouts"),
        "location" : os.path.join(DIR_DATA_EXTERNAL, "location"),
        "SA_processed" : os.path.join(DIR_DATA_EXTERNAL, "SA_processed"),
        "SA_raw" : os.path.join(DIR_DATA_EXTERNAL, "SA_raw"),
        "samples" : os.path.join(DIR_DATA_EXTERNAL, "samples"),
        "specs" : os.path.join(DIR_DATA_EXTERNAL, "device_specs"),
        "tariffs" : os.path.join(DIR_DATA_EXTERNAL, "tariffs"),
        "gas" : os.path.join(DIR_DATA_EXTERNAL, "tariffs_gas"),
        "control" : os.path.join(DIR_DATA_EXTERNAL, "control"),
        "weather" : os.path.join(DIR_DATA_EXTERNAL, "weather"),
        }
    DIR_RESULTS = os.path.join(DIR_MAIN, "results")
    DIR_PROJECTS = os.path.join(DIR_MAIN, "projects")
    
    DIR_METEONORM = os.path.join("C:/TRNSYS18/Weather/Meteonorm/Australia-Oceania")
    FILES_METEONORM = {
        "Adelaide": "AU-Adelaide-946720.tm2",
        "Alice_Spring": "AU-Alice-Springs-943260.tm2",
        "Brisbane": "AU-Brisbane-945780.tm2",
        "Canberra": "AU-Canberra-949260.tm2",
        "Darwin": "AU-Darwin-Airport-941200.tm2",
        "Hobart": "AU-Hobart-Airport-949700.tm2",
        "Melbourne": "AU-Melbourne-948660.tm2",
        "Perth": "AU-Perth-946080.tm2",
        "Sydney": "AU-Sydney-947680.tm2",
        "Townsville": "AU-Townsville-942940.tm2",
    }

    #FILES
    FILES_MODEL_SPECS = {
        "resistive" : os.path.join(DIR_DATA["specs"], "data_models_RS.csv"),
        "heat_pump" : os.path.join(DIR_DATA["specs"], "data_models_HP.csv"),
        "gas_instant": os.path.join(DIR_DATA["specs"], "data_models_GI.csv"),
        "gas_storage": os.path.join(DIR_DATA["specs"], "data_models_GS.csv"),
        "solar_thermal": os.path.join(DIR_DATA["specs"], "data_models_TH.csv"),
    }

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
    FILE_GAS_TARIFF_SAMPLE = os.path.join(DIR_DATA["gas"],"energyaustralia_basic.json")
    

class DEFAULT():

    LOCATION = "Sydney"
    HWDP = 1
    NEM_REGION = "NSW1"
    
    TZ = 'Australia/Brisbane'       # NEM timezone
    LAT = -33.86
    LON = 151.21
    TILT = abs(LAT)
    ORIENT = 180.
    
    G_STC = 1000.                   #[W/m2]
    PV_NOMPOW = 5000.               #[W]
    ADR_PARAMS = {
        'k_a': 0.99924,
        'k_d': -5.49097,
        'tc_d': 0.01918,
        'k_rs': 0.06999,
        'k_rsh': 0.26144,
    }

class SIMULATIONS_IO():

    TS_TYPES = {
        "weather": ["GHI", "temp_amb", "temp_mains", "DNI", "DHI", "WS"],
        "control": ["CS"],
        "electric": ["PV_gen", "import_grid", "import_CL"],
        "HWDP": ["P_HWD", "m_HWD", "m_HWD_day"],
        "economic": ["tariff", "rate_type", "wholesale_market"],
        "emissions": ["intensity_index", "marginal_index"],
    }
    TS_COLUMNS_ALL = [
        item for sublist in 
            [value for _, value in TS_TYPES.items()]
        for item in sublist
    ]

    TS_TYPES_TM = ["weather", "control", "HWDP"]    # ts columns for thermal sims
    TS_TYPES_PV = ["weather", "electric"]                   # ts columns for PV sim
    TS_TYPES_ECO = ["weather", "economic", "emissions"]     # ts columns for ECO postproc

    # PARAMS_OUT = [
    #     'heater_heat_acum', 'heater_power_acum', 'heater_perf_avg',
    #     'E_HWD_acum', 'eta_stg', 'cycles_day', 'SOC_avg',
    #     'm_HWD_avg', 'temp_amb_avg', 'temp_mains_avg',
    #     'SOC_min', 'SOC_025', 'SOC_050', 't_SOC0',
    #     'emissions_total', 'emissions_marginal', 'solar_ratio',
    # ]
    OUTPUT_SIM_PV = [
        "poa_global",
        "temp_pv",
        "eta_rel",
        "pv_power"
    ]
    OUTPUT_CONTROL = [
        "CS",
        "pv_to_hw",
        "CS_nopv",
    ]

    OUTPUT_SIM_DEWH = [
        'heater_heat',
        'heater_power',
        'heater_perf',
        'tank_flow_rate',
        'tank_temp_out',
        'C_all',
        'tank_temp_avg',         # T_avg in trnsys. CHANGE!
        'SOC',
        'SOC2',
        'SOC3',
        'E_HWD',
        'E_level',
    ]
    OUTPUT_SIM_STC = [
        "",
    ]
    OUTPUT_ANALYSIS_TM =[
        "heater_heat_acum", "heater_power_acum", "heater_perf_avg",
        "E_HWD_acum", "E_losses_acum",
        "eta_stg", "cycles_day",
        "SOC_avg", "SOC_min", "SOC_025", "SOC_050", "t_SOC0",
    ]
    OUTPUT_ANALYSIS_ECON = [
        'annual_emissions_total',
        'annual_emissions_marginal',
        'solar_ratio_potential',
        'solar_ratio_real',
        'annual_hw_household_cost',
        'annual_hw_retailer_cost'
    ]
    OUTPUT_ANALYSIS_FIN = [
        "net_present_cost",
        "payback_period",
        "LCOHW",
        "capital_cost",
        "annual_energy_cost",
        "daily_supply_cost",
        "oandm_cost",
        "others_cost",
        "rebates",
        "disconnection_costs",
    ]

    FIN_COMP_OUTPUT = [
        "emission_savings",
        "cost_savings_household",
        "cost_savings_retailer",
    ]


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
    DNSPS = [
        "Actewagl", "Ausgrid", "Ausnet", "CitiPower", "Endeavour",
        "Essential", "Energex", "Ergon", "Evoenergy", "Horizon", "Jemena",
        "Powercor", "Powerwater", "SAPN", "TasNetworks", "Unitedenergy", "Western",
    ]
    LOCATIONS_DNSP = {
        "Adelaide": "SAPN",
        "Brisbane": "Energex",
        "Canberra": "Evoenergy",
        "Darwin": "Powerwater",
        "Melbourne": "CitiPower",
        "Perth": "Western",
        "Sydney": "Ausgrid",
        "Townsville": "Ergon",
    }
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
    STATES_NEM_REGION = {
        "SA":"SA1", "NSW": "NSW1", "QLD":"QLD1", "VIC": "VIC1",
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
    
    TARIFF_TYPES = {
        "flat": "Flat Tariff",
        "tou": "Time of Use",
        "CL" : "Controlled Load",
    }
    CONTROL_TYPES = {
        "GS": "general supply",
        "CL": "controlled load",
        "CL1": "controlled load 1",
        "CL2": "controlled load 2",
        "CL3": "controlled load, solar soak option",
        "timer": "timer",
        "timer_SS": "timer for solar soak",
        "timer_OP": "timer for off-peak periods (tou)",
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
    HWDP_NAMES = {
        1:'Mor & Eve Only',
        2:'Mor & Eve w daytime',
        3:'Evenly',
        4:'Morning',
        5:'Evening',
        6:'late Night',
    }
    