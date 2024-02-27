import os
import sys
import random
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    TypedDict,
)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy
import cartopy.crs as ccrs                   # import projections
import cartopy.feature as cf                 # import features

from tm_solarshift.external import solarshift_sola_data
DATA_DIRECTORY = solarshift_sola_data.DATA_DIRECTORY
prepare_site_data_in_df = solarshift_sola_data.prepare_site_data_in_df

from tm_solarshift.external import energy_plan_utils
get_energy_plan_for_dnsp = energy_plan_utils.get_energy_plan_for_dnsp
get_energy_breakdown = energy_plan_utils.get_energy_breakdown
add_wholesale_prices = energy_plan_utils.add_wholesale_prices

# from tm_solarshift.external import model_constants


# from SA_Solarshift_data import (
#     DATA_DIRECTORY,
#     prepare_site_data_in_df
#     )
# from energy_plan_utils import (
#     get_energy_plan_for_dnsp,
#     get_energy_breakdown,
#     add_wholesale_prices,
# )
from model_constants import SolarShiftConstants
(
    NUM_TSTAMP_IN_DAY,
    POWER_THRESHOLDS,
    SEASON_DEFINITION,
    SYSTEM_NAME_MAPPING,
    SECONDS_PER_HOUR,
    HOURS_PER_DAY,
    DAYS_PER_YEAR,
    KWH_TO_WH,
    LOAD_CONSISTENCY_CONSTANT,
    MIN_MAX_POWER_RATIO,
    NUM_FLEXIBLE_INCREASE_PERIODS,
    NUM_FLEXIBLE_DECREASE_PERIODS,
    DNSPS,
    CONTROLLED_LOAD_INFO,
) = (
    SolarShiftConstants.NUM_TSTAMP_IN_DAY,
    SolarShiftConstants.POWER_THRESHOLDS,
    SolarShiftConstants.SEASON_DEFINITION,
    SolarShiftConstants.SYSTEM_NAME_MAPPING,
    SolarShiftConstants.SECONDS_PER_HOUR,
    SolarShiftConstants.HOURS_PER_DAY,
    SolarShiftConstants.DAYS_PER_YEAR,
    SolarShiftConstants.KWH_TO_WH,
    SolarShiftConstants.LOAD_CONSISTENCY_CONSTANT,
    SolarShiftConstants.MIN_MAX_POWER_RATIO,
    SolarShiftConstants.NUM_FLEXIBLE_INCREASE_PERIODS,
    SolarShiftConstants.NUM_FLEXIBLE_DECREASE_PERIODS,
    SolarShiftConstants.DNSPS,
    SolarShiftConstants.CONTROLLED_LOAD_INFO,
)

from tm_solarshift.devices import Variable
from tm_solarshift.constants import (
    DIRECTORY,
    PROFILES,
    DEFINITIONS,
    UNITS
)
DIR_DATA = DIRECTORY.DIR_DATA
PROFILES_TYPES = PROFILES.TYPES
DEFINITION_SEASON = DEFINITIONS.SEASON
LOCATIONS_METEONORM = DEFINITIONS.LOCATIONS_METEONORM
CF = UNITS.conversion_factor

from tm_solarshift.general import GeneralSetup
from tm_solarshift.devices import Variable
from tm_solarshift.weather import (
        Weather,
        load_dataset_merra2,
        )


W2kJh = 3.6
pd.set_option('display.max_columns', None)

AUS_PROJ = 3112
NSW_PROJ = 3308
AUS_BOUNDS = [110.,155.,-45.,-10.]
AUS_BOUNDS_noWA = [128., 155.,-45.,-10.]
NSW_BOUNDS = [138.,154.,-38.,-28.]
colors = {'WA':'red', 'SA':'gold', 'NT':'orange', 'QLD':'maroon', 'VIC':'darkblue', 'NSW':'dodgerblue', 'TAS':'green', 'ACT': 'blue'}


#----------------------
#Getting the site list
def exploring_site_list():
    included_system_types = [
        "resistive_water_heater",
        ]

    site_id_list = None
    site_list = pd.read_csv(
        os.path.join(
            DATA_DIRECTORY.sa_data_dirs["raw_data"],
            DATA_DIRECTORY.sa_file_names["site_list"],
        ),
        index_col=False,
    )
    class_list = pd.read_csv(
        os.path.join(
            DATA_DIRECTORY.sa_data_dirs["processed_data"],
            DATA_DIRECTORY.sa_file_names["site_hot_water_classification"],
        ),
        index_col=False,
    )
    site_list = site_list.merge(
        class_list.loc[:, ["site_id", "hw_system_type"]],
        on="site_id",
        how="left",
    )

    site_list_filtered = site_list[
        (site_list['hw_system_type'].isin(included_system_types))
    ].reset_index(drop=True)


    all_stats = pd.read_csv(
        os.path.join(
            DATA_DIRECTORY.sa_data_dirs["processed_data"],
            DATA_DIRECTORY.sa_file_names["site_basic_stats"],
        ) )

    all_stats = all_stats[
        ["site_id",
        "daily_hot_water_mean",
        "daily_hot_water_min",
        "daily_hot_water_max",]
    ]

    site_list_filtered.index = site_list_filtered["site_id"]
    all_stats.index = all_stats["site_id"]
    all_stats.drop("site_id",axis=1,inplace=True)
    site_list_filtered.drop("site_id",axis=1,inplace=True)

    site_stats = site_list_filtered.merge(
        all_stats,
        how='left',
        left_index=True,
        right_index=True
    )
    return site_stats

#--------------
def plotting_site_stats(site_stats: pd.DataFrame, showfig: bool = True):
    eta_stg_avg = 0.65
    Temp_Mains = 20.
    Temp_Cons = 45.
    cp = 4.18

    site_stats['m_HWD_day_avg'] = (
        site_stats['daily_hot_water_mean']
        * eta_stg_avg / (cp * (Temp_Cons - Temp_Mains))
        * 3600.
        )
    site_stats['m_HWD_day_max'] = (
        site_stats['daily_hot_water_max']
        * eta_stg_avg / (cp * (Temp_Cons - Temp_Mains))
        * 3600.
        )

    fig, ax = plt.subplots(figsize=(9,6))
    fs=16
    ax.hist(site_stats['m_HWD_day_avg'],bins=10,density=False)
    ax.set_xlabel( 'Average daily consumption (kg/day)', fontsize=fs)
    ax.set_ylabel( 'Number of sites', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    ax.grid()
    if showfig:
        plt.show()
    plt.close()

    fig, ax = plt.subplots(figsize=(9,6))
    fs=16
    ax.hist(site_stats['m_HWD_day_max'],bins=10,density=False)
    ax.set_xlabel( 'Maximum daily consumption (kg/day)', fontsize=fs)
    ax.set_ylabel( 'Number of sites', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    ax.grid()
    if showfig:
        plt.show()
    plt.close()
    return

#--------------
def get_hw_dataframe(site_id: int, showfig:bool = True) -> pd.DataFrame:

    start_date = pd.to_datetime("2023-01-01 00:00:00")
    end_date = pd.to_datetime("2023-02-01 00:00:00")

    data_types = ["pv", "load", "hot_water"]
    daily_data_types = [
        "pv",
        "load",
        "hot_water",
        "grid_export",
        "grid_import",
    ]
    metrics = ["mean", "min", "max", "std", "median"]
    daily_metrics = ["mean", "min", "max", "std", "median"]
    site_data = prepare_site_data_in_df(
        site_id,
        start_date = start_date,
        end_date = end_date,
        data_types = data_types,
        data_dir = DATA_DIRECTORY.sa_data_dirs["raw_data"],
    )

    return site_data

def get_daily_values(site_data: pd.DataFrame, showfig:bool = True) -> pd.DataFrame:

    hw_day = site_data.groupby(site_data.t_stamp.dt.date, dropna=False)['hot_water'].sum() / 1000. #[kWh]
    hw_day["m_HWD_day"] = (
        hw_day['hot_water']
        * eta_stg_avg / (cp * (Temp_Cons - Temp_Mains))
        * 3600.
        )

    fig, ax = plt.subplots(figsize=(9,6))
    fs = 16
    hw_day.sort_values(ascending=True,inplace=True)
    hw_day_hist = hw_day.reset_index()

    eta_stg_avg = 0.65
    Temp_Mains = 20.
    Temp_Cons = 45.
    cp = 4.18
    hw_day_hist['m_HWD_day'] = (
        hw_day_hist['hot_water']
        * eta_stg_avg / (cp * (Temp_Cons - Temp_Mains))
        * 3600.
        )

    ax.plot(hw_day_hist.index,hw_day_hist.m_HWD_day,lw=2.0)
    ax.set_xlabel( 'Day of the year (day)', fontsize=fs)
    ax.set_ylim( 0, 500)
    ax.set_ylabel( 'Daily Consumption (kg/day)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    ax.grid()
    if showfig:
        plt.show()
    plt.close()
    return hw_day

#----------------
def get_location_SolA_sites() -> pd.DataFrame:
    df_sitesinfo = pd.read_csv(Weather.FILES["SOLA_CL_INFO"])
    
    df_postcodes = pd.read_csv(Weather.FILES["postcodes"])
    df_postcodes = df_postcodes.groupby("postcode")[["long","lat"]].mean()
    
    df_sitesinfo["lon"] = df_postcodes["long"].loc[df_sitesinfo["postcode"]].to_list()
    df_sitesinfo["lat"] = df_postcodes["lat"].loc[df_sitesinfo["postcode"]].to_list()
    
    df_sitesinfo.index = df_sitesinfo["site_id"]
    df_sitesinfo.to_csv(Weather.FILES["SOLA_POSTCODES_INFO"])
    return df_sitesinfo

#---------------
def plot_SolA_locations(
        file_sites: str = None,
        showfig: bool = False,
        savefig: bool = True,
) -> None:

    if file_sites is None:
        file_sites = Weather.FILES["SOLA_POSTCODES_INFO"]
        
    f_s = 16
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111,projection=ccrs.epsg(AUS_PROJ))
    ax.set_extent(AUS_BOUNDS)
    ax.set_title("SolA dataset sites. Locations")
    res='50m'
    ocean = cf.NaturalEarthFeature('physical', 'ocean', res, edgecolor='face', facecolor= cf.COLORS['water'])
    lakes = cf.NaturalEarthFeature('physical', 'lakes', res, edgecolor='k', facecolor= cf.COLORS['water'], lw=0.5)
    borders = cf.NaturalEarthFeature('cultural', 'admin_1_states_provinces', res, facecolor='none', edgecolor='k', lw=0.5)
    
    ax.add_feature(borders)
    ax.add_feature(ocean)
    ax.add_feature(lakes)
    ax.add_feature(cf.COASTLINE)

    df_sites = pd.read_csv(file_sites)
    for state in DEFINITIONS.STATES.keys():
        df_state = df_sites[df_sites["state"]==state]
        ax.scatter(
            df_state["lon"],df_state["lat"],
            transform=ccrs.PlateCarree(), c = colors[state], s=10,
            label=f"{state} ({len(df_state)} sites)",
            )
    ax.legend()

    if showfig:
        plt.show()
    if savefig:
        fig.savefig(
            os.path.join("SolA_locations.png"),
            bbox_inches="tight",
        )
    return None


def plot_SolAsites_merra2(
        file_sites: str = None,
        file_merra2: str = Weather.FILES["MERRA2"],
        showfig: bool = True,
        savefig: bool = True,
        
) -> None:

    mms = ['o','*','.',',','x','X','+','P','s','D','d','p','H']

    if file_sites is None:
        file_sites = Weather.FILES["SOLA_POSTCODES_INFO"]
    
    df_sites = pd.read_csv(file_sites, index_col=0)
    YEAR = 2023
    MONTH = 1
    
    f_s = 16
    fig, axes = plt.subplots(1,2, figsize=(12, 6))
    (ax1,ax2) = axes

    i = 0
    for (idx, row) in df_sites.iterrows():
        site_id = idx
        state = row["state"]
        lon = row["lon"]
        lat = row["lat"]

        try:
            #load the dataframe with hw_circuit and filter for January 2023
            df_hw = get_hw_dataframe(site_id)
            df_hw.index = df_hw.t_stamp

            #Load the df_merra 
            df_merra = load_dataset_merra2(
                ts = df_hw,
                location = (lon,lat),
                YEAR = 2023,
                file_dataset=file_merra2
                )
            print(df_merra)

            hw_day = df_hw.groupby(df_hw.t_stamp.dt.date, dropna=False)['hot_water'].sum() / 1000. #[kWh]
            cols = ['hot_water','Temp_Amb', 'GHI']
            df_day = df_merra.groupby(
                df_merra.t_stamp.dt.date, dropna=False
                )[cols].sum()
            df_day["hot_water"] = df_day["hot_water"]/1000. #[kWh/day]

            df_count = df_merra.groupby(
                df_merra.t_stamp.dt.date, dropna=False
                )[cols].count()
            df_day["Temp_Amb"] = df_day["Temp_Amb"] / df_count["Temp_Amb"] #degC
            df_day["GHI"] = df_day["GHI"] *(1/12.) /1000.  #kWh
            df_day = df_day.sort_values("hot_water")
            df_day = df_day[df_day["hot_water"]>0.1]
            ax1.scatter(df_day["hot_water"], df_day["Temp_Amb"], s=5)
            ax2.scatter(df_day["hot_water"], df_day["GHI"], s=5)
            # ax1.plot(df_day["hot_water"], df_day["Temp_Amb"], lw=1, ms=5)
            # ax2.plot(df_day["hot_water"], df_day["GHI"], lw=1, ms=5)
            i+=1
            print(i)
        except Exception as e:
            print(e)
            pass
        
        if i==200:
            break

    ax1.set_ylabel("Ambient Temperature daily avg", fontsize=f_s)
    ax2.set_ylabel("GHI, daily avg", fontsize=f_s)
    ax1.set_xlabel("HW electric daily consumption (kWh)", fontsize=f_s)
    ax2.set_xlabel("HW electric daily consumption (kWh)", fontsize=f_s)
    if savefig:
        fig.savefig(
            # os.path.join("SolA_MERRA_Jan2023_lines.png"),
            os.path.join("SolA_MERRA_Jan2023_dots_alot.png"),
            bbox_inches="tight",
        )
    if showfig:
        plt.show()
    

    plt.close()
    return None


def main():
    GS = GeneralSetup()
    GS.simulation.YEAR = Variable(2020,"-")

    get_location_SolA_sites()
    plot_SolA_locations( Weather.FILES["SOLA_POSTCODES_INFO"], showfig=True )

    file_merra2 = os.path.join(Weather.FLDR["MERRA2"], "MERRA2_Processed_2023.nc")
    plot_SolAsites_merra2(file_merra2=file_merra2, showfig=True)

    site_stats = exploring_site_list()
    plotting_site_stats(site_stats, showfig=False)

    site_id = 998800275
    get_hw_dataframe(site_id)
    
    return
    

if __name__ == "__main__":
    main()


sys.exit()

for site_id in site_stats.index:
    print(site_id)
    
    site_data = prepare_site_data_in_df(
        site_id,
        # start_date = None,
        # end_date = None,
        data_types = data_types,
        data_dir = DATA_DIRECTORY.sa_data_dirs["raw_data"],
    )
    break

#### SHOWING AN EXAMPLE
idx = 998800275
fig, ax = plt.subplots(figsize=(9,6))
data_site =  prepare_site_data_in_df(
    idx,
    data_types=["pv", "load", "hot_water"],
    data_dir=DATA_DIRECTORY.sa_data_dirs["raw_data"],
)
hw_day = data_site.groupby(data_site.t_stamp.dt.date, dropna=False)['hot_water'].sum() / 1000.
hw_day.sort_values(ascending=True,inplace=True)
hw_day_hist = hw_day.reset_index()

eta_stg_avg = 0.65
Temp_Mains = 20.
Temp_Cons = 45.
cp = 4.18
hw_day_hist['m_HWD_day'] = (
    hw_day_hist['hot_water']
    * eta_stg_avg / (cp * (Temp_Cons - Temp_Mains))
    * 3600.
    )

ax.plot(hw_day_hist.index,hw_day_hist.m_HWD_day,lw=2.0)
ax.set_xlabel( 'Day of the year (day)', fontsize=fs)
ax.set_ylim( 0, 500)
ax.set_ylabel( 'Daily Consumption (kg/day)', fontsize=fs)
ax.tick_params(axis='both', which='major', labelsize=fs)
ax.grid()
plt.show()

sys.exit()
##############################################


print(site_stats)

fig, ax = plt.subplots(figsize=(9,6))
bins = 10
rangex = (0,5)
yavg = np.zeros(bins)
Nsample = len(site_stats)
i=0
fig, ax = plt.subplots(figsize=(9,6))
for idx,site in site_stats.iterrows():
    try:
        data_site =  prepare_site_data_in_df(
            idx,
            data_types=["pv", "load", "hot_water"],
            data_dir=DATA_DIRECTORY.sa_data_dirs["raw_data"],
        )
        hw_day = data_site.groupby(data_site.t_stamp.dt.date, dropna=False)['hot_water'].sum() / 1000.
        
        hw_day.sort_values(ascending=True,inplace=True)
        hw_day_hist = hw_day.reset_index()
        
        eta_stg_avg = 0.65
        Temp_Mains = 20.
        Temp_Cons = 45.
        cp = 4.18
        hw_day_hist['m_HWD_day'] = (
            hw_day_hist['hot_water']
            * eta_stg_avg / (cp * (Temp_Cons - Temp_Mains))
            * 3600.
            )
        
        ax.plot(hw_day_hist.index,hw_day_hist.m_HWD_day,lw=0.5)
    except:
        print(f"{idx} couldnt be accessed")
ax.set_xlabel( 'Day of the year (day)', fontsize=fs)
ax.set_ylim( 0, 600)
ax.set_ylabel( 'Daily Consumption (kg/day)', fontsize=fs)
ax.tick_params(axis='both', which='major', labelsize=fs)
ax.grid()
plt.show()


    # # data_site['time'] = pd.to_datetime(data_site.t_stamp)
    # try:
    #     hw_day = data_site.groupby(data_site.t_stamp.dt.date, dropna=False)['hot_water'].sum() / 1000.
        
        
    #     dx = (rangex[1]-rangex[0])/bins
    #     hw_day = hw_day / hw_day.mean()
    #     hw_dist = np.histogram(hw_day,bins=bins, density=True, range=rangex)
    #     # hw_dist[1] = [(hw_dist[1][i]+hw_dist[1][i+1])/2 for i in range(len(hw_dist[1])-1)]
    #     yavg = yavg + hw_dist[0]*dx
    #     ax.plot(hw_dist[1][:-1],hw_dist[0]*dx,lw=1.0)
    # except:
    #     print(f'{site_id} without data')
    # i+=1
# ax.plot(hw_dist[1][:-1],yavg/Nsample,lw=3,c='k',ls='--')

#Fitting a Weibull distribution

# ax.set_xlabel( 'Daily hot water draw (divided by avg)', fontsize=fs)
# ax.set_ylabel( 'Density Function', fontsize=fs)
# ax.tick_params(axis='both', which='major', labelsize=fs)
# ax.grid()
# plt.show()

sys.exit()