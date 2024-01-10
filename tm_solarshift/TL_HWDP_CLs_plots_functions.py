# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 12:01:13 2023

@author: z5158936
"""

import subprocess           # to run the TRNSYS simulation
import shutil               # to duplicate the output txt file
import time                 # to measure the computation time
import os
import datetime
import sys 
import glob

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

##############################################################
fs=16
locations_few = ['Sydney','Brisbane','Melbourne','Townsville','Adelaide']
mm = ['o','v','s','d','P','*','H']
HWDP_names = {1:'Mor & Eve Only',
              2:'Mor & Eve w daytime',
              3:'Evenly',
              4:'Morning',
              5:'Evening',
              6:'late Night'}
CL_names = {0:'GS',
            1:'CL1',
            2:'CL2',
            3:'CL3',
            4:'SS'}
colors = ['red','orange','green','darkblue','dodgerblue','maroon']

##########################################
# STORAGE EFFICIENCY: BARS PLOT

def plot_storage_efficiency_bars(
        results,
        savefig=False,
        width=0.1,
        location_legend='Sydney',
        locations=locations_few
        ):

    widths = [-2.5*width, -1.5*width, -0.5*width, 0.5*width, 1.5*width, 2.5*width]
    for location in locations:
        fig, ax = plt.subplots(figsize=(9,6))
        i=0
        for profile_HWD in list_profile_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            ax.bar(aux.profile_control + widths[i], aux.eta_stg,
                   width, color=f'C{i}', alpha=0.8,
                   label=HWDP_names[profile_HWD])
            i+=1
        
        ax.set_title(location,fontsize=fs+2)
        ax.grid()
        # if location=='Sydney':
        #     ax.legend(bbox_to_anchor=(1.01, 0.8),fontsize=fs-2)
        if location==location_legend:
            ax.legend(
                loc='lower center',
                bbox_to_anchor=(0.5, -0.35),
                fontsize=fs-2,
                ncols=3)
                
        ax.set_ylim(0.5,0.8)
        ax.set_xticks(list_profile_control)
        ax.set_xticklabels(CL_names.values(), rotation=45)
        ax.set_xlabel( 'Type of Control Load', fontsize=fs)
        ax.set_ylabel( 'Storage efficiency', fontsize=fs)
        ax.tick_params(axis='both', which='major', labelsize=fs)
        # ax.set_ylim(-0.0002,0.0)
        if savefig:
            fig.savefig(
                os.path.join(
                    fldr_rslt,'0-eta_stg_'+location+'.png'
                    ),
                bbox_inches='tight')
        plt.show()
    return

########################################
def plot_heater_energy_bars(
        results,
        savefig=False,
        width=0.1,
        location_legend='Sydney',
        locations=locations_few
        ):
    
    widths = [-2.5*width, -1.5*width, -0.5*width, 0.5*width, 1.5*width, 2.5*width]
    N_CSs = len(list_profile_control)
    
    for location in locations:
        fig, ax = plt.subplots(figsize=(9,6))
        i=0
        for profile_HWD in list_profile_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            ax.bar(aux.profile_control + widths[i], aux.heater_heat_acum,
                   width, color=f'C{i}', alpha=0.8, 
                   label=HWDP_names[profile_HWD])
            i+=1
        
        E_Heater_baseline = results[
            (results.location==location)&
            (results.profile_control==1)
            ]['heater_heat_acum'].mean()
        E_Heater_CL = results[
            (results.location==location)
            ].groupby('profile_control')['heater_heat_acum'].mean()
        
        E_Heater_pct = E_Heater_CL / E_Heater_baseline - 1
        for i in range(N_CSs):
            ax.text(i-2*width, E_Heater_CL.loc[i]+100,
                    f'{E_Heater_pct.loc[i]:.2%}' , fontsize=fs)
        
        i=1
        ax.plot([0+widths[0], (N_CSs-1) + widths[-1]],
                [E_Heater_CL.loc[i], E_Heater_CL.loc[i]],
                ls=':', c='k',lw=2,
                label=r'$E_{heater}$ CL1')
        
        aux = results[(results.location==location)]
        ax.set_ylim(0.,3700)
        xmn,xmx = ax.get_xlim()
        E_HWD_min = aux.E_HWD_acum.min()
        
        ax.plot([xmn,xmx],[E_HWD_min,E_HWD_min],
                c='red',lw=3,
                label=r'$E_{HWD}$')
        
        ax.set_title(location,fontsize=fs+4)
        ax.grid()
        
        if location==location_legend:
            ax.legend(
                loc='lower center',
                bbox_to_anchor=(0.5, -0.44),
                fontsize=fs-2,
                ncols=3)
        
        ax.set_xticks(list_profile_control)
        ax.set_xticklabels(CL_names.values(), rotation=45)
        ax.set_xlabel( 'Type of Control Load', fontsize=fs)
        ax.set_ylabel( 'Annual energy consumed by heater (kWh/yr)', fontsize=fs)
        ax.tick_params(axis='both', which='major', labelsize=fs)
        # ax.set_ylim(-0.0002,0.0)
        if savefig:
            fig.savefig(
                os.path.join(
                    fldr_rslt,'0-E_Heater_'+location+'.png'
                    ),
                bbox_inches='tight')
        plt.show()
    return

########################################
def plot_SOC_minimum_scatter(
        results,
        savefig=False,
        width=0.1,
        location_legend='Sydney',
        locations=locations_few
        ):
    
    for location in locations:
        fig, ax = plt.subplots(figsize=(9,6))
        i=0
        for profile_HWD in list_profile_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            ax.scatter(aux.profile_control, aux.SOC_min,
                       s=100,marker=mm[profile_HWD],
                       label=HWDP_names[profile_HWD])
            i+=1
        ax.set_title(location,fontsize=fs+2)
        ax.grid()
        if location=='Sydney':
            ax.legend(bbox_to_anchor=(1.01, 0.8),fontsize=fs-2)
        
        ax.set_ylim(0.0,1.0)
        ax.set_xticks(list_profile_control)
        ax.set_xticklabels(CL_names.values(), rotation=45)
        ax.set_xlabel( 'Type of Control Load', fontsize=fs)
        ax.set_ylabel( 'Minimum SOC', fontsize=fs)
        ax.tick_params(axis='both', which='major', labelsize=fs)
        # ax.set_ylim(-0.0002,0.0)
        if savefig:
            fig.savefig(
                os.path.join(
                    fldr_rslt,'0-SOC_min_'+location+'.png'
                    ),
                bbox_inches='tight')
            
        plt.show()
    return

##########################################
def plot_annual_energy_in_out(
        results,
        savefig=False
        ):
    fig, ax = plt.subplots(figsize=(9,6))
    j=0
    for location in list_location:
        i=0
        for profile_HWD in list_profile_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            lbl = location if profile_HWD==1 else None
            ax.scatter(aux.E_HWD_acum, aux.heater_heat_acum,
                       label=lbl,marker=mm[i],c='C'+str(j),s=100)
            i+=1
        j+=1
        
    ax.grid()
    ax.legend(loc=0,fontsize=fs)
    ax.set_xlabel('Annual energy in HWDP (kWh)', fontsize=fs)
    ax.set_ylabel('Annual energy in Resistive heater (kWh)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    if savefig:
        fig.savefig(
            os.path.join(
                fldr_rslt,'0-Annual_Energy_HeaterVsHWD.png'
                ),
            bbox_inches='tight')
    plt.show()
    return

########################################
def plot_etastg_vs_SOC(
        results,
        savefig=False,
        ):
    
    fig, ax = plt.subplots(figsize=(9,6))
    j=0
    for location in locations_few:
        i=0
        for profile_HWD in list_profile_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            if profile_HWD==1:
                ax.scatter(aux.eta_stg,aux.SOC_min,
                           marker=mm[profile_HWD], c='C'+str(j), s=100,
                           label=location)
            else:
                ax.scatter(aux.eta_stg,aux.SOC_min,
                           marker=mm[profile_HWD], c='C'+str(j), s=50)
            i+=1
        j+=1
    
    ax2 = ax.twinx()
    i=0
    for HWDP in HWDP_names:
        ax2.scatter([],[],c='gray',marker=mm[i],label=HWDP_names[i+1])
        i+=1
    ax2.legend(bbox_to_anchor=(1.45, 1.0),fontsize=fs-2)
    ax2.set_yticks([])
    ax.grid()
    ax.legend(loc=0,fontsize=fs)
    ax.set_xlabel('Storage efficiency', fontsize=fs)
    ax.set_ylabel('Minimum SOC', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    if savefig:
        fig.savefig(
            os.path.join(
                fldr_rslt,'0-Eta_stg_Vs_SOC_min.png'
                ),
            bbox_inches='tight')
    plt.show()
    return

##################################################
def plot_annual_energy_Tmains(
        results,
        savefig=False,
        ):
    fig, ax = plt.subplots(figsize=(9,6))
    j=0
    for location in list_location:
        i=0
        for profile_HWD in list_profile_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            if profile_HWD==1:
                ax.scatter(aux.temp_mains_avg, aux.eta_stg,
                           marker=mm[profile_HWD],c='C'+str(j),s=100,
                           label=location)
            else:
                ax.scatter(aux.temp_mains_avg, aux.eta_stg,
                           marker=mm[profile_HWD], c='C'+str(j),s=50)
            i+=1
        j+=1
    
    ax.grid()
    ax.legend(loc=0,fontsize=fs)
    ax.set_xlabel('Annual average mains temperature (C)', fontsize=fs)
    ax.set_ylabel('Storage efficiency', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    if savefig:
        fig.savefig(
            os.path.join(
                fldr_rslt,'0-Annual_Energy_eta_Tmains.png'
                ),
            bbox_inches='tight')
    plt.show()
    return


def plot_total_emissions_one_location(
        results,
        savefig=False,
        location='Sydney',
        width=0.1
        ):
    
    widths = [-2.5*width, -1.5*width, -0.5*width, 0.5*width, 1.5*width, 2.5*width]
    
    fig, ax = plt.subplots(figsize=(9,6))
    i=0
    for profile_HWD in list_profile_HWD:
        aux = results[
            (results.location==location)&
            (results.profile_HWD==profile_HWD)
            ]
        ax.bar(aux.profile_control + widths[i], aux.emissions_total,
               width, color=f'C{i}', alpha=0.8,
               label=HWDP_names[profile_HWD])
        i+=1
    
    ax.set_title(location,fontsize=fs+2)
    ax.grid()
    if location=='Sydney':
        ax.legend(bbox_to_anchor=(1.01, 0.8),fontsize=fs-2)
    
    ax.set_ylim(0.0,2.5)
    ax.set_xticks(list_profile_control)
    ax.set_xticklabels(CL_names.values(), rotation=45)
    ax.set_xlabel( 'Type of Control Load', fontsize=fs)
    ax.set_ylabel( r'Anual accumulated Emissions (t-$CO_2$-e)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    # ax.set_ylim(-0.0002,0.0)
    if savefig:
        fig.savefig(
            os.path.join(
                fldr_rslt,'0-Emissions_'+location+'.png'
                ),
            bbox_inches='tight')
    plt.show()
    return


def plot_total_emissions_diff_locations(
        results,
        savefig=False,
        list_location=['Adelaide','Brisbane','Melbourne','Sydney'],
        profile_HWD = 3,
        width=0.15
        ):

    widths = [-1.5*width, -0.5*width, 0.5*width, 1.5*width]
    fig, ax = plt.subplots(figsize=(9,6))
    i=0
    for location in list_location:
        aux = results[
            (results.location==location)&
            (results.profile_HWD==profile_HWD)
            ]
        ax.bar(aux.profile_control + widths[i], aux.emissions_total,
               width, color=f'C{i}', alpha=0.8,
               label=location)
        
        reduction = 1 - aux[aux.profile_control==4].emissions_total.values[0] /aux[aux.profile_control==1].emissions_total.values[0]
        print(f'{reduction*100:.1f}%')
        i+=1
    
    ax.set_title('Different cities with HWDP=3',fontsize=fs+2)
    ax.grid()
    ax.legend(bbox_to_anchor=(1.01, 0.8),fontsize=fs-2)
    
    ax.set_ylim(0.0,3.0)
    ax.set_xticks(list_profile_control)
    ax.set_xticklabels(CL_names.values(), rotation=45)
    ax.set_xlabel( 'Type of Control Load', fontsize=fs)
    ax.set_ylabel( r'Anual accumulated Emissions (t-$CO_2$-e)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    # ax.set_ylim(-0.0002,0.0)
    if savefig:
        fig.savefig(
            os.path.join(
                fldr_rslt,'0-Emissions_all.png'
                ),
            bbox_inches='tight')
    plt.show()

########################################
#### GENERATING PLOTS


#Defining conditions for plots
list_profile_HWD = [1,2,3,4,5,6]
list_profile_control = [0,1,2,3,4]
list_location = ['Sydney', 'Adelaide', 'Brisbane', 'Melbourne', 'Canberra', 'Darwin', 'Perth', 'Townsville']

fldr_rslt = 'Parametric_HWDP_CL_Resistive'
file_rslts = '0-Parametric_HWDP_CL_Resistive.csv'

results = pd.read_csv(
    os.path.join(
        fldr_rslt,file_rslts),
    index_col=0
    )

savefig = True

plot_storage_efficiency_bars(results, savefig=savefig)
plot_heater_energy_bars(results, savefig=savefig)
plot_SOC_minimum_scatter(results, savefig=savefig)
plot_annual_energy_in_out(results, savefig=savefig)
plot_etastg_vs_SOC(results, savefig=savefig)
plot_annual_energy_Tmains(results, savefig=savefig)
plot_total_emissions_one_location(results, savefig=savefig)
plot_total_emissions_diff_locations(results, savefig=savefig)

sys.exit()































# #####################################################
# #####################################################
# df_varEH = pd.DataFrame([],columns=CL_names, index=list_location)
# #Determining the variation for all the cities
# for (x,y) in [(x,y) for x in list_location for y in CL_names ]:
#     E_Heater_baseline = results[
#                         (results.location==x)&
#                         (results.profile_control==1)
#                         ]['E_Heater_acum'].mean()
#     E_Heater_CL = results[
#                         (results.location==x)&
#                         (results.profile_control==y)
#                         ]['E_Heater_acum'].mean()
    
#     df_varEH.loc[x,y] = (E_Heater_CL / E_Heater_baseline - 1)*100

# df_varEH.rename(columns=CL_names, inplace=True)
# file_varEH = os.path.join(fldr_rslt,'0-var_E_Heater_fromCL1.csv')
# df_varEH.to_csv(file_varEH)

# ##########################################
# # sys.exit()



# #####################################
