# -*- coding: utf-8 -*-
"""
Created on Thu Dec  7 08:16:57 2023

@author: z5158936
"""

# -*- coding: utf-8 -*-
"""
Created on Mon Aug 14 18:15:34 2023

@author: z5158936
"""

import nemed
from nemed.downloader import download_aemo_cdeii_summary, download_unit_dispatch
from nemed.process import aggregate_data_by

# To generate plots shown 
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Open plot in browser (optional)
import plotly.io as pio
# pio.renderers.default = "browser"

import time                 # to measure the computation time
import os
import datetime
import sys 

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy import stats
import tm_solarshift.trnsys_utils as TRP

fileDir = os.path.dirname(os.path.abspath(__file__))
emissionsDir = os.path.join(fileDir,"data","emissions")
CacheDir = os.path.join(os.path.dirname(fileDir),'TEMPCACHE_nemed_demo')
pd.set_option('display.max_columns', None)

type_index = "marginal"

for (type_index, year) in [
        (type_index, year)
        for type_index in ["total", "marginal"]
        for year in range(2019,2023)
        ]:
    #### Plotting a sample of Intensity_Index
    if type_index == "total":
        file_emissions = os.path.join(emissionsDir, f'emissions_year_{year}_total.csv')
        if not(os.path.isfile(file_emissions)):
            emissions = nemed.get_total_emissions(start_time=f"{year}/01/01 00:00",
                                                end_time=f"{year}/12/31 23:59",
                                                cache=CacheDir,
                                                filter_regions=['NSW1','VIC1','SA1','QLD1'])
            
            emissions.index = pd.to_datetime(emissions.TimeEnding)
            emissions.drop(columns=['TimeEnding'],inplace=True)
            emissions.to_csv( file_emissions )
        else:
            emissions = pd.read_csv(file_emissions,index_col=0)
            emissions.index = pd.to_datetime(emissions.index)
    
    
    if type_index == "marginal":
        file_emissions = os.path.join(emissionsDir, f'emissions_year_{year}_marginal.csv')
        if not(os.path.isfile(file_emissions)):
            emissions = nemed.get_marginal_emissions(start_time=f"{year}/01/01 00:00",
                                                end_time=f"{year}/12/31 23:59",
                                                cache=CacheDir,
                                                )
            
            emissions.index = pd.to_datetime(emissions.Time)
            emissions.drop(columns=['Time'],inplace=True)
            emissions.rename(
                columns = {"Intensity_Index":"Marginal_Index"},
                inplace = True
                )
            emissions.to_csv( file_emissions )
        else:
            emissions = pd.read_csv(file_emissions,index_col=0)
            emissions.index = pd.to_datetime(emissions.index)
    
    
    #### Plotting a sample of Intensity_Index
    fig, ax = plt.subplots(figsize=(9,6))
    i=0
    ax.plot(emissions.index, emissions.Intensity_Index,
            lw=3, ls='-', marker='o', c='C0', ms=10)
    
    N_days = 5
    dstart = datetime.datetime(2022,1,1)
    dend = datetime.datetime(2022,1,1+N_days)
    ax.set_xlim(dstart,dend)    
    ax.grid()
    plt.show()
    
