import numpy as np


class SolarShiftConstants:
    NUM_TSTAMP_IN_DAY = 288
    SECONDS_PER_HOUR = 3600
    KWH_TO_WH = 1000
    HOURS_PER_DAY = 24
    DAYS_PER_YEAR = 365
    POWER_THRESHOLDS = {
        "heat_pump_low": 0.5,
        "heat_pump_high": 1.4,
        "electric_heater_low": 1.4,
        "electric_heater_high": 10,
        "instantaneous_heater_low": 10,
        "auxiliary_heater_low": 1.0,
    }
    SEASON_DEFINITION = {
        "summer": [12, 1, 2],
        "autumn": [3, 4, 5],
        "winter": [6, 7, 8],
        "spring": [9, 10, 11],
    }
    LOAD_CONSISTENCY_CONSTANT = (
        0.00005  # constant to increase load consistency
    )
    MIN_MAX_POWER_RATIO = 0.9  # threshold between min and max hot water power
    NUM_FLEXIBLE_INCREASE_PERIODS = 4  # number of flexible increase periods
    NUM_FLEXIBLE_DECREASE_PERIODS = 10  # number of flexible decrease periods
    # clustering parameters
    RANDOM_STATE = 0
    NUMPY_FUNCTIONS = {
        "mean": np.mean,
        "median": np.median,
        "max": np.max,
        "min": np.min,
    }
    HOURS_IN_DAY = 24
    SECONDS_IN_HOUR = 3600
    # weekday/weekend definition
    DAYOFWEEK_DEFINITION = {"weekday": [0, 1, 2, 3, 4], "weekend": [5, 6]}
    # climate zone definition
    CLIMATE_ZONE_DEFINITION = {
        1: "Hot humid summer",
        2: "Warm humid summer",
        3: "Hot dry summer, mild winter",
        4: "Hot dry summer, cold winter",
        5: "Warm summer, cool winter",
        6: "Mild warm summer, cold winter",
    }
    SYSTEM_NAME_MAPPING = {
        "heat_pump_auxiliary_heater": "Heat Pump + Auxiliary Heater",
        "auxiliary_heater": "Resistive + Auxiliary Heater",
        "PV_diverter": "PV Diverter",
        "resistive_water_heater_with_diverter": "Resistive Heater + Diverter",
        "heat_pump": "Heat Pump",
        "resistive_water_heater": "Resistive Heater",
        "solar_thermal_boost": "Solar hot water + Booster",
        "unknown": "Unknown",
    }
    DNSPS = [
        "Actewagl",
        "Ausgrid",
        "Ausnet",
        "CitiPower",
        "Endeavour",
        "Essential",
        "Energex",
        "Ergon",
        "Horizon",
        "Jemena",
        "Powercor",
        "Powerwater",
        "SAPN",
        "TasNetworks",
        "Unitedenergy",
        "Western",
    ]
    DNSP_NAME_MAPPING = {
        "Actewagl": "Evoenergy",
        "Ausgrid": "Ausgrid",
        "Ausnet": "Ausnet",
        "CitiPower": "CitiPower",
        "Endeavour": "Endeavour",
        "Essential": "Essential",
        "Energex": "Energex",
        "Ergon": "Ergon",
        "Horizon": "Horizon Power",
        "Jemena": "Jemena",
        "Powercor": "Powercor",
        "Powerwater": "PowerWater",
        "SAPN": "SAPN",
        "TasNetworks": "TasNetworks",
        "Unitedenergy": "United Energy",
        "Western": "Western Power",
    }

    AUS_STATES = [
        "ACT",
        "NSW",
        "NT",
        "QLD",
        "SA",
        "TAS",
        "VIC",
        "WA",
    ]
    ACTEWAGL_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.17171,
                        "time_periods": [
                            ["22:00", "23:59"],
                            ["00:00", "06:59"],
                        ],
                        "duration_hours": 8,
                    },
                    {
                        "rate": 0.17171,
                        "time_periods": [
                            ["09:00", "16:59"],
                        ],
                        "duration_hours": 5,
                    },
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    AUSGRID_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.17,
                        "time_periods": [
                            ["22:00", "23:59"],
                            ["00:00", "06:59"],
                        ],
                        "duration_hours": 6,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    AUSGRID_CONTROLLED_LOAD_2 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.17,
                        "time_periods": [
                            ["20:00", "23:59"],
                            ["00:00", "16:59"],
                        ],
                        "duration_hours": 16,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    ENDEAVOUR_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.1958,
                        "time_periods": [
                            ["22:00", "23:59"],
                            ["00:00", "06:59"],
                        ],
                        "duration_hours": 9,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.077,
            }
        ],
    }

    ENDEAVOUR_CONTROLLED_LOAD_2 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.1571,
                        "time_periods": [
                            ["00:00", "23:59"],
                        ],
                        "duration_hours": 17,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.077,
            }
        ],
    }

    ESSENTIAL_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.1744,
                        "time_periods": [
                            ["00:00", "23:59"],
                        ],
                        "duration_hours": 9,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.1349,
            }
        ],
    }

    ESSENTIAL_CONTROLLED_LOAD_2 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.1744,
                        "time_periods": [
                            ["00:00", "23:59"],
                        ],
                        "duration_hours": 19,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.1349,
            }
        ],
    }

    ENERGEX_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.2061,
                        "time_periods": [
                            ["22:00", "23:59"],
                            ["00:00", "06:59"],
                        ],
                        "duration_hours": 8,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    ENERGEX_CONTROLLED_LOAD_2 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.2061,
                        "time_periods": [
                            ["00:00", "15:59"],
                            ["20:00", "23:59"],
                        ],
                        "duration_hours": 18,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    ERGON_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.17266,
                        "time_periods": [
                            ["00:00", "23:59"],
                        ],
                        "duration_hours": 8,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    ERGON_CONTROLLED_LOAD_2 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.19140,
                        "time_periods": [
                            ["00:00", "23:59"],
                        ],
                        "duration_hours": 18,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    SAPN_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.201,
                        "time_periods": [
                            ["23:00", "23:59"],
                            ["00:00", "06:59"],
                        ],
                        "duration_hours": 6,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    AUSNET_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.1962,
                        "time_periods": [
                            ["20:00", "23:59"],
                            ["00:00", "07:59"],
                        ],
                        "duration_hours": 8,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    CITIPOWER_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.1566,
                        "time_periods": [
                            ["21:30", "23:59"],
                            ["00:00", "06:59"],
                        ],
                        "duration_hours": 8,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    JEMENA_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.1761,
                        "time_periods": [
                            ["20:00", "23:59"],
                            ["00:00", "07:59"],
                        ],
                        "duration_hours": 8,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    POWERCOR_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.1656,
                        "time_periods": [
                            ["21:30", "23:59"],
                            ["00:00", "06:59"],
                        ],
                        "duration_hours": 8,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    UNITED_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.1631,
                        "time_periods": [
                            ["20:00", "23:59"],
                            ["00:00", "07:59"],
                        ],
                        "duration_hours": 8,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.0,
            }
        ],
    }

    TASNETWORKS_CONTROLLED_LOAD_1 = {
        "energy_charges": [
            {
                "charge_type": "plan",
                "tariff_type": "controlled_load",
                "season": "all",
                "currency": "AUD",
                "rate_details": [
                    {
                        "rate": 0.13607,
                        "time_periods": [
                            ["22:00", "23:59"],
                            ["00:00", "06:59"],
                        ],
                        "duration_hours": 9,
                    }
                ],
            }
        ],
        "service_charges": [
            {
                "service_name": "daily_supply_charge",
                "rate_type": "daily",
                "currency": "AUD",
                "rate": 0.21793,
            }
        ],
    }

    CONTROLLED_LOAD_INFO = {
        "Actewagl": {"controlled_load_1": ACTEWAGL_CONTROLLED_LOAD_1},
        "Ausgrid": {
            "controlled_load_1": AUSGRID_CONTROLLED_LOAD_1,
            "controlled_load_2": AUSGRID_CONTROLLED_LOAD_2,
        },
        "Endeavour": {
            "controlled_load_1": ENDEAVOUR_CONTROLLED_LOAD_1,
            "controlled_load_2": ENDEAVOUR_CONTROLLED_LOAD_2,
        },
        "Ergon": {
            "controlled_load_1": ERGON_CONTROLLED_LOAD_1,
            "controlled_load_2": ERGON_CONTROLLED_LOAD_2,
        },
        "Essential": {
            "controlled_load_1": ESSENTIAL_CONTROLLED_LOAD_1,
            "controlled_load_2": ESSENTIAL_CONTROLLED_LOAD_2,
        },
        "Energex": {
            "controlled_load_1": ENERGEX_CONTROLLED_LOAD_1,
            "controlled_load_2": ENERGEX_CONTROLLED_LOAD_2,
        },
        "Ausnet": {"controlled_load_1": AUSNET_CONTROLLED_LOAD_1},
        "SAPN": {"controlled_load_1": SAPN_CONTROLLED_LOAD_1},
        "Jemena": {"controlled_load_1": JEMENA_CONTROLLED_LOAD_1},
        "Unitedenergy": {"controlled_load_1": UNITED_CONTROLLED_LOAD_1},
        "Powercor": {"controlled_load_1": POWERCOR_CONTROLLED_LOAD_1},
        "TasNetworks": {"controlled_load_1": TASNETWORKS_CONTROLLED_LOAD_1},
        "CitiPower": {"controlled_load_1": CITIPOWER_CONTROLLED_LOAD_1},
    }

    EE_DATA_TYPES = {
        "energy": ["Active Energy", "Reactive Energy"],
        "power": ["Active Power", "Reactive Power"],
        "circuit_details": [
            "Average Voltage",
            "Average Current",
            "Average Impedance",
            "Average THD",
            "Average Phase Angle",
            "Maximum Voltage",
            "Minimum Voltage",
            "Maximum Current",
            "Minimum Current",
        ],
        "instantaneous": [
            "Instantaneous Voltage",
            "Instantaneous Net Active Power",
            "Instantaneous Net Reactive Power",
            "Instantaneous Active Controlled Load",
            "Instantaneous Reactive Controlled Load",
        ],
    }
    EE_PHASE_TYPES = [
        "A Phase",
        "Export",
        "Import",
        "C Phase",
        "Total",
        "B Phase",
    ]
    EE_DEFAULT_START_DATE = "2022-04-01"
    EE_DEFAULT_END_DATE = "2023-01-31"
    EE_CL_PATTERN = r"CL(\d+)"
    EE_VPP_PATTERN = r"VPP(\d+)"
