# -*- coding: utf-8 -*-
"""
Created on Mon Jun 19 19:52:33 2023

@author: z5158936
"""

import os
import copy
import pandas as pd

import tm_solarshift.general as general
import tm_solarshift.trnsys as trnsys
import tm_solarshift.profiles as profiles
import tm_solarshift.profiles as devices

PROFILES_TYPES = profiles.PROFILES_TYPES
PROFILES_COLUMNS = profiles.PROFILES_COLUMNS

PARAMS_OUT = ['heater_heat_acum', 'heater_power_acum', 'heater_perf_avg',
            'E_HWD_acum', 'eta_stg', 'cycles_day', 'SOC_avg',
            'm_HWD_avg', 'temp_amb_avg', 'temp_mains_avg',
            'SOC_min', 'SOC_025', 'SOC_050', 't_SOC0',
            'emissions_total','solar_ratio']

DATA_DIR = general.DATA_DIR
DIR_RESULTS = "results"

pd.set_option('display.max_columns', None)

#################################################
def parametric_run(
    runs_in,
    params_in,
    params_out,
    general_setup_base = general.GeneralSetup(),
    case_template=None,
    case_vars=[],
    save_results_detailed  = False,
    fldr_results_detailed  = None,
    gen_plots_detailed     = False,
    save_plots_detailed    = False,
    save_results_general   = False,
    file_results_general   = None,
    fldr_results_general   = None,
    append_results_general = False,       #If false, create new file
    verbose = True,
    ):
    
    runs = runs_in.copy()
    
    if append_results_general:
        runs_old = pd.read_csv(
            os.path.join(
                DIR_RESULTS, fldr_results_general, file_results_general
                )
            ,index_col=0
            )
      
    for index, row in runs.iterrows():
        
        print(f'RUNNING SIMULATION {index+1}/{len(runs)}')
        
        general_setup = copy.copy(general_setup_base)
        
        #Updating parameters
        cols_in = params_in.keys()
        general_setup.update_params(row[cols_in])
        
        location = general_setup.location
        profile_HWD = general_setup.profile_HWD
        profile_control = general_setup.profile_control
        random_control = general_setup.random_control
        YEAR = general_setup.YEAR

        if verbose:
            print("Creating Profiles for Simulation")
        Profiles = profiles.profiles_new(general_setup)
        Profiles = profiles.HWDP_generator_standard(
            Profiles,
            HWD_daily_dist = profiles.HWD_daily_distribution(general_setup, Profiles),
            HWD_hourly_dist = profile_HWD
        )
        
        file_weather = os.path.join(
            DATA_DIR["weather"], "meteonorm_processed",
            f"meteonorm_{location}.csv",
        )
        Profiles = profiles.load_weather_from_file(Profiles, file_weather)
        
        Profiles = profiles.load_control_load(
            Profiles, 
            profile_control = profile_control, 
            random_ON = random_control
        )
        
        file_emissions = os.path.join(
            DATA_DIR["emissions"],
            f"emissions_year_{YEAR}.csv"
        )
        Profiles = profiles.load_emission_index(
            Profiles, 
            file_emissions = file_emissions,
            location = location
        )
        
        Profiles = profiles.load_PV_generation(Profiles)
        Profiles = profiles.load_elec_consumption(Profiles)
        
        if verbose:
            print("Executing TRNSYS simulation")
        out_data = trnsys.thermal_simulation_run(general_setup, Profiles)
        out_overall = trnsys.postprocessing_annual_simulation(
            general_setup, Profiles, out_data
        )
        values_out = [out_overall[lbl] for lbl in params_out]
        runs.loc[index, params_out] = values_out
        
        aux = [getattr(general_setup,x) for x in case_vars]
        case = case_template.format(*aux)
        
        ###########################################
        #General results?
        if save_results_general:
            fldr = os.path.join(DIR_RESULTS,fldr_results_general)
            if not os.path.exists(fldr):
                os.mkdir(fldr)
                
            if append_results_general:
                runs_save = pd.concat([runs_old,runs],ignore_index=True)
                runs_save.to_csv(
                    os.path.join(fldr,file_results_general)
                    )
            else:
                runs.to_csv(
                    os.path.join(fldr,file_results_general)
                    )
                
        ###########################################
        #Detailed results?
        if save_results_detailed:
            fldr = os.path.join(DIR_RESULTS,fldr_results_detailed)
            if not os.path.exists(fldr):
                os.mkdir(fldr)
            out_data.to_csv(os.path.join(fldr,case+'_Results.csv'))
    
        ############################################
        #Detailed plots?
        if gen_plots_detailed:
            trnsys.detailed_plots(
                general_setup,
                out_data,
                fldr_results_detailed = fldr_results_detailed,
                case = case,
                save_plots_detailed = save_plots_detailed
                )
            
        print(runs.loc[index])
        
    return runs


def main():
    print()
    print("NEW PARAMETRIC ANALYSIS")
    print()

def parametric_run_HP():
    list_profile_HWD = [1,2,3,4,5,6]
    list_profile_control = [0,1,2,3,4]
    list_location = ['Sydney', 'Adelaide', 'Brisbane', 'Melbourne'] #, 'Canberra', 'Darwin', 'Perth', 'Townsville']
    
    case_template = '{}-{}-{}-{}_{}_HWD-{}_CL-{}'
    case_vars = ['layout_DEWH', 'layout_PV', 'layout_TC', 'layout_WF', 
                  'location', 'profile_HWD', 'profile_control']
    
    params_in = {
        'profile_HWD'      : list_profile_HWD,
        'profile_control'  : list_profile_control,
        'location'         : list_location,
        }
    
    runs = general.parametric_settings(params_in, PARAMS_OUT)
    
    general_setup_base = general.GeneralSetup(
        DEWH = devices.HeatPump()
        )
    
    runs = parametric_run(
        runs, params_in, PARAMS_OUT,
        Sim_base = general_setup_base,
        case_template = case_template,
        case_vars = case_vars,
        save_results_detailed = True,
        gen_plots_detailed    = True,
        save_plots_detailed   = True,
        save_results_general  = True,
        fldr_results_detailed = 'Parametric_HWDP_CL_HeatPump',
        fldr_results_general  = 'Parametric_HWDP_CL_HeatPump',
        file_results_general  = '0-Parametric_HWDP_CL_HeatPump.csv',
        append_results_general = False      #If false, create new file
        )

if __name__ == "__main__":
    # main()
    parametric_run_HP()
################################################
# #### Parametric Analysis: Tank
#     list_heater_nom_cap = np.array([2400., 3600., 4800.])
#     list_tank_temp_high = np.array([55., 60., 65., 70.])
#     list_tank_U        = np.array([0.5, 1.0, 2.0])
#     list_tank_vol      = np.array([0.1, 0.3, 0.5])
#     list_HWD_avg       = np.array([100,200,300,400])
    
#     case_template = 'Heater-{:.0f}_TempHigh-{:.0f}_U-{:.2f}_Vol-{:.3f}_HWD-{:.0f}'
#     case_vars = ['Heater_NomCap','Tank_TempHigh','Tank_U','Tank_Vol','HWD_avg']
    
#     params_in = {
#         'Heater_NomCap'  : list_heater_nom_cap,
#         'Tank_TempHigh'  : list_tank_temp_high,
#         'Tank_Vol'       : list_tank_vol,
#         'Tank_U'         : list_tank_U,
#         'HWD_avg'        : list_HWD_avg,
#         }
    
#     runs = trnsys.parametric_settings(params_in, PARAMS_OUT)
    
#     Sim_base = trnsys.TRNSYS_Setup(
#             profile_HWD     = 1,
#             profile_control = 1
#             )
    
#     runs = Parametric_Run(
#         runs, params_in, PARAMS_OUT,
#         Sim_base = Sim_base,
#         case_template=case_template,
#         case_vars=case_vars,
#         save_results_detailed = False,
#         gen_plots_detailed    = True,
#         save_plots_detailed   = True,
#         save_results_general  = True,
#         fldr_results_detailed = 'Results_Parametric_Tank',
#         fldr_results_general  = 'Results_Parametric_Tank',
#         file_results_general  = 'Results_Param_Tank.csv',
#         append_results_general = False       #If false, create new file
#         )

################################################
################################################
#### Parametric Analysis Volume, HWD and CLs
    # list_Tank_Vol        = np.array([0.1, 0.2, 0.3, 0.4])
    # list_HWD_avg         = np.array([100,200,300,400])
    # list_profile_control = np.array([0,1,2,3,4,5])
    
    # case_template = 'Control-{:}_TankVol-{:.2f}_HWD-{:.0f}'
    # case_vars = ['profile_control','Tank_Vol','HWD_avg']
    
    # params_in = {
    #     'Tank_Vol'        : list_Tank_Vol,
    #     'HWD_avg'         : list_HWD_avg,
    #     'profile_control' : list_profile_control
    #     }
    
    # params_out = ['E_HWD_acum', 'E_Heater_acum',
    #             'eta_stg', 'Cycles_day', 'SOC_avg', 'SOC2_avg', 'SOC3_avg',
    #             'm_HWD_avg', 'T_amb_avg', 'T_mains_avg',
    #             'SOC_min', 'SOC_025', 'SOC_050', 't_SOC0']
    
    # runs = trnsys.Parametric_Settings(params_in, params_out)
    
    # runs = Parametric_Run(
    #     runs, params_in, params_out,
    #     case_template = case_template,
    #     case_vars = case_vars,
    #     save_results_detailed = True,
    #     gen_plots_detailed    = True,
    #     save_plots_detailed   = True,
    #     save_results_general  = True,
    #     fldr_results_detailed = 'Results_Parametric_CS',
    #     fldr_results_general  = 'Results_Parametric_CS',
    #     file_results_general  = '0-Results_Parametric_CS.csv',
    #     append_results_general = False       #If false, create new file
    #     )
################################################
################################################

################################################
#### Resistive Heater Simulation
#### HWDP_CLs: Original set
    # list_profile_HWD = [1,2,3,4,5,6]
    # list_profile_control = [0,1,2,3,4]
    # list_location = list_location = ['Sydney', 'Adelaide', 'Brisbane', 'Melbourne', 'Canberra', 'Darwin', 'Perth', 'Townsville']
    
    # case_template = '{}-{}-{}-{}_{}_HWD-{}_CL-{}'
    # case_vars = ['layout_DEWH', 'layout_PV', 'layout_TC', 'layout_WF', 
    #               'location', 'profile_HWD', 'profile_control']
    
    # params_in = {
    #     'location'         : list_location,
    #     'profile_HWD'      : list_profile_HWD,
    #     'profile_control'  : list_profile_control,
    #     }
    
    # runs = trnsys.parametric_settings(params_in, PARAMS_OUT)
    
    # runs = parametric_run(
    #     runs, params_in, PARAMS_OUT,
    #     case_template = case_template,
    #     case_vars = case_vars,
    #     save_results_detailed = True,
    #     gen_plots_detailed    = True,
    #     save_plots_detailed   = True,
    #     save_results_general  = True,
    #     fldr_results_detailed = 'Parametric_HWDP_CL_Resistive',
    #     fldr_results_general  = 'Parametric_HWDP_CL_Resistive',
    #     file_results_general  = '0-Parametric_HWDP_CL_Resistive.csv',
    #     append_results_general = False       #If false, create new file
    #     )

###############################################
###############################################
#### HP SIMULATIONS



################################################
#### INCLUDING TARIFFS HP

    # list_profile_HWD     = [1,2,3,4,5,6]
    # list_DNSP = ["Actewagl", "Ausgrid", "Ausnet", "CitiPower", "Endeavour",
    #               "Essential","Energex","Ergon","Horizon","Jemena","Powercor",
    #               "Powerwater","SAPN","TasNetworks","Unitedenergy","Western",]
    
#     list_tariff_type = ['flat','tou']
    
#     case_template = '{}-{}-{}-{}_{}_HWD-{}_{}_{}'
#     case_vars = ['layout_DEWH', 'layout_PV', 'layout_TC', 'layout_WF', 
#                   'location', 'profile_HWD','DNSP','tariff_type']
    
#     params_in = {
#         'profile_HWD'  : list_profile_HWD,
#         # 'profile_control'  : list_profile_control,
#         'DNSP'         : list_DNSP,
#         'tariff_type'  : list_tariff_type
#         }
    
#     # params_out = params_out + ['Total_Elec_Cost']
    
#     runs = trnsys.Parametric_Settings(params_in, params_out)
    
#     Sim_base = trnsys.General_Setup(
#         layout_DEWH   = 'HPF',
#         Heater_NomCap = 5240,
#         Heater_F_eta  = 6.02,
#         Tank_TempHigh = 63.,
#         Tank_TempHighControl = 59.,
#         location='Sydney',
#         profile_control = 0,
#         DNSP = 'Ausgrid',
#         tariff_type='flat',
#         # STOP=120,
#         )
#     # Sim_base = trnsys.TRNSYS_Setup()
    
#     runs = Parametric_Run(
#         runs, params_in, params_out,
#         Sim_base = Sim_base,
#         case_template = case_template,
#         case_vars = case_vars,
#         save_results_detailed = True,
#         gen_plots_detailed    = True,
#         save_plots_detailed   = True,
#         save_results_general  = True,
#         fldr_results_detailed = 'Tariffs',
#         fldr_results_general  = 'Tariffs',
#         file_results_general  = '0-HP_Tariffs.csv',
#         append_results_general = False      #If false, create new file
#         )

# #######################################################
# #### INCLUDING TARIFFS RESISTIVE
#     list_profile_HWD     = [1,2,3,4,5,6]
#     list_DNSP = ["Actewagl", "Ausgrid", "Ausnet", "CitiPower", "Endeavour",
#                   "Essential","Energex","Ergon","Horizon","Jemena","Powercor",
#                   "Powerwater","SAPN","TasNetworks","Unitedenergy","Western",]
#     list_tariff_type = ['flat','tou']
    
#     case_template = '{}-{}-{}-{}_{}_HWD-{}_{}_{}'
#     case_vars = ['layout_DEWH', 'layout_PV', 'layout_TC', 'layout_WF', 
#                   'location', 'profile_HWD','DNSP','tariff_type']
    
#     params_in = {
#         'profile_HWD'  : list_profile_HWD,
#         'DNSP'         : list_DNSP,
#         'tariff_type'  : list_tariff_type
#         }
    
#     # params_out = params_out + ['Total_Elec_Cost']
    
#     runs = trnsys.Parametric_Settings(params_in, params_out)
    
#     # Sim_base = trnsys.General_Setup(
#     #     layout_DEWH   = 'HPF',
#     #     Heater_NomCap = 5240,
#     #     Heater_F_eta  = 6.02,
#     #     Tank_TempHigh = 63.,
#     #     Tank_TempHighControl = 59.,
#     #     location='Sydney',
#     #     profile_control = 0,
#     #     DNSP = 'Ausgrid',
#     #     tariff_type='flat',
#     #     # STOP=120,
#     #     )
#     Sim_base = trnsys.TRNSYS_Setup(
#         layout_DEWH   = 'RS',
#         profile_control = 0,
#         DNSP = 'Ausgrid',
#         tariff_type='flat'
#         )
    
#     runs = Parametric_Run(
#         runs, params_in, params_out,
#         Sim_base = Sim_base,
#         case_template = case_template,
#         case_vars = case_vars,
#         save_results_detailed = True,
#         gen_plots_detailed    = True,
#         save_plots_detailed   = True,
#         save_results_general  = True,
#         fldr_results_detailed = 'Tariffs',
#         fldr_results_general  = 'Tariffs',
#         file_results_general  = '0-RS_Tariffs.csv',
#         append_results_general = False      #If false, create new file
#         )

################################################
##### TESTING

    # list_profile_HWD = [1,2,3,4,5,6]
    # list_profile_control = [0]
    # list_location = ['Sydney']
    
    # case_template = '{}-{}-{}-{}_{}_HWD-{}_CL-{}'
    # case_vars = ['layout_DEWH', 'layout_PV', 'layout_TC', 'layout_WF', 
    #               'location', 'profile_HWD', 'profile_control']
    
    # params_in = {
    #     'profile_HWD'      : list_profile_HWD,
    #     'profile_control'  : list_profile_control,
    #     'location'         : list_location,
    #     }
    
    # runs = trnsys.Parametric_Settings(params_in, params_out)
    
    # Sim_base = trnsys.TRNSYS_Setup(
    #     layout_DEWH   = 'HPF',
    #     Heater_NomCap = 5240,
    #     Heater_F_eta  = 6.02,
    #     Tank_TempHigh = 63.,
    #     Tank_TempHighControl = 59.,
    #     )
    # # Sim_base = trnsys.TRNSYS_Setup()
    
    # runs = Parametric_Run(
    #     runs, params_in, params_out,
    #     Sim_base = Sim_base,
    #     case_template = case_template,
    #     case_vars = case_vars,
    #     save_results_detailed = True,
    #     gen_plots_detailed    = True,
    #     save_plots_detailed   = True,
    #     save_results_general  = True,
    #     fldr_results_detailed = 'Testing',
    #     fldr_results_general  = 'Testing',
    #     file_results_general  = '0-Testing.csv',
    #     append_results_general = False      #If false, create new file
    #     )