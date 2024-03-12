import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import List

from tm_solarshift.general import (HWDP_NAMES, CL_NAMES,MAIN_DIR)

#---------------------------------------

fs=16
LIST_PROFILE_HWD = [1,2,3,4,5,6]
LIST_PROFILE_CONTROL = [0,1,2,3,4]
LOCATIONS_FEW = ['Sydney','Brisbane','Melbourne','Adelaide']
mm = ['o','v','s','d','P','*','H']
colors = ['red','orange','green','darkblue','dodgerblue','maroon']

#---------------------------------------

def plot_storage_efficiency_bars(
        results: pd.DataFrame,
        fldr_fig: str,
        savefig: bool = False,
        showfig: bool = False,
        width: float = 0.1,
        location_legend: str ='Sydney',
        locations: List = LOCATIONS_FEW
        ):

    widths = [-2.5*width, -1.5*width, -0.5*width, 0.5*width, 1.5*width, 2.5*width]
    for location in locations:
        fig, ax = plt.subplots(figsize=(9,6))
        i=0
        for profile_HWD in LIST_PROFILE_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            ax.bar(aux.profile_control + widths[i], aux.eta_stg,
                   width, color=f'C{i}', alpha=0.8,
                   label=HWDP_NAMES[profile_HWD])
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
        ax.set_xticks(LIST_PROFILE_CONTROL)
        ax.set_xticklabels(CL_NAMES.values(), rotation=45)
        ax.set_xlabel( 'Type of Control Load', fontsize=fs)
        ax.set_ylabel( 'Storage efficiency', fontsize=fs)
        ax.tick_params(axis='both', which='major', labelsize=fs)
        # ax.set_ylim(-0.0002,0.0)
        if savefig:
            fig.savefig(
                os.path.join(
                    fldr_fig,'0-eta_stg_'+location+'.png'
                    ),
                bbox_inches='tight')
        if showfig:
            plt.show()
        plt.close()
    return

#---------------------------------------
def plot_heater_energy_bars(
        results: pd.DataFrame,
        fldr_fig: str,
        savefig: bool = False,
        showfig: bool = False,
        width: float = 0.1,
        location_legend: str ='Sydney',
        locations: List = LOCATIONS_FEW,
        ):
    
    widths = [-2.5*width, -1.5*width, -0.5*width, 0.5*width, 1.5*width, 2.5*width]
    N_CSs = len(LIST_PROFILE_CONTROL)
    
    for location in locations:
        fig, ax = plt.subplots(figsize=(9,6))
        i=0
        for profile_HWD in LIST_PROFILE_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            ax.bar(aux.profile_control + widths[i], aux.heater_heat_acum,
                   width, color=f'C{i}', alpha=0.8, 
                   label=HWDP_NAMES[profile_HWD])
            
            ax.bar(aux.profile_control + widths[i], aux.heater_power_acum,
                   width, hatch='//', color=f'C{i}', alpha=0.8,
                   label=None)
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
        ax.set_ylim(0.,3500)
        xmn,xmx = ax.get_xlim()
        E_HWD_min = aux.E_HWD_acum.min()
        
        ax.plot([xmn,xmx],[E_HWD_min,E_HWD_min],
                c='red',lw=3,
                label=r'$E_{HWD}$')
        
        ax.bar(np.NaN, np.NaN, color='none', hatch='//', label='HP Power')
        ax.grid()
        
        if location==location_legend:
            ax.legend(
                loc='lower center',
                bbox_to_anchor=(0.5, -0.44),
                fontsize=fs-2,
                ncols=3)
        
        ax.set_xticks(LIST_PROFILE_CONTROL)
        ax.set_xticklabels(CL_NAMES.values(), rotation=45)
        ax.set_xlabel( 'Type of Control Load', fontsize=fs)
        ax.set_ylabel( 'Annual energy delivered by HP (kWh/yr)', fontsize=fs)
        ax.tick_params(axis='both', which='major', labelsize=fs)
        # ax.set_ylim(-0.0002,0.0)
        if savefig:
            fig.savefig(
                os.path.join(
                    fldr_fig,'0-E_Heater_'+location+'.png'
                    ),
                bbox_inches='tight')
        if showfig:
            plt.show()
        plt.close()
    return

#---------------------------------------
def plot_SOC_minimum_scatter(
        results: pd.DataFrame,
        fldr_fig: str,
        savefig: bool = False,
        showfig: bool = False,
        width: float = 0.1,
        location_legend: str ='Sydney',
        locations: List = LOCATIONS_FEW,
        ):
    
    for location in locations:
        fig, ax = plt.subplots(figsize=(9,6))
        i=0
        for profile_HWD in LIST_PROFILE_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            ax.scatter(aux.profile_control, aux.SOC_min,
                       s=100,marker=mm[profile_HWD],
                       label=HWDP_NAMES[profile_HWD])
            i+=1
        ax.set_title(location,fontsize=fs+2)
        ax.grid()
        if location=='Sydney':
            ax.legend(bbox_to_anchor=(1.01, 0.8),fontsize=fs-2)
        
        ax.set_ylim(0.0,1.0)
        ax.set_xticks(LIST_PROFILE_CONTROL)
        ax.set_xticklabels(CL_NAMES.values(), rotation=45)
        ax.set_xlabel( 'Type of Control Load', fontsize=fs)
        ax.set_ylabel( 'Minimum SOC', fontsize=fs)
        ax.tick_params(axis='both', which='major', labelsize=fs)
        # ax.set_ylim(-0.0002,0.0)
        if savefig:
            fig.savefig(
                os.path.join(
                    fldr_fig,'0-SOC_min_'+location+'.png'
                    ),
                bbox_inches='tight')
            
        if showfig:
            plt.show()
        plt.close()
    return

#---------------------------------------
def plot_COP_avg_scatter(
        results: pd.DataFrame,
        fldr_fig: str,
        savefig: bool = False,
        showfig: bool = False,
        width: float = 0.1,
        location_legend: str ='Sydney',
        locations: List = LOCATIONS_FEW,
        ):
    
    for location in locations:
        fig, ax = plt.subplots(figsize=(9,6))
        i=0
        for profile_HWD in LIST_PROFILE_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            ax.scatter(aux.profile_control, aux.heater_perf_avg,
                       s=100,marker=mm[profile_HWD],
                       label=HWDP_NAMES[profile_HWD])
            i+=1
        # ax.set_title(location,fontsize=fs+2)
        ax.grid()
        
        if location==location_legend:
            ax.legend(
                loc='lower center',
                bbox_to_anchor=(0.5, -0.44),
                fontsize=fs-2,
                ncols=3)
        
        ax.set_ylim(2.0,4.0)
        ax.set_xticks(LIST_PROFILE_CONTROL)
        ax.set_xticklabels(CL_NAMES.values(), rotation=45)
        ax.set_xlabel( 'Type of Control Load', fontsize=fs)
        ax.set_ylabel( 'Annual Average COP', fontsize=fs)
        ax.tick_params(axis='both', which='major', labelsize=fs)
        # ax.set_ylim(-0.0002,0.0)
        if savefig:
            fig.savefig(
                os.path.join(
                    fldr_fig,'0-COP_avg_'+location+'.png'
                    ),
                bbox_inches='tight')
        if showfig:
            plt.show()
        plt.close()
    return

#---------------------------------------
def plot_Annual_Energy_InOut(
        results: pd.DataFrame,
        fldr_fig: str,
        savefig: bool = False,
        showfig: bool = False,
        ):
    fig, ax = plt.subplots(figsize=(9,6))
    j=0
    for location in LOCATIONS_FEW:
        i=0
        for profile_HWD in LIST_PROFILE_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            lbl = location if profile_HWD==1 else None
            ax.scatter(aux.E_HWD_acum,aux.heater_power_acum,
                       label=lbl,marker=mm[i],c='C'+str(j),s=100)
            i+=1
        j+=1
        
    ax.grid()
    ax.legend(loc=0,fontsize=fs)
    ax.set_xlabel('Annual energy in HWDP (kWh)', fontsize=fs)
    ax.set_ylabel('Annual energy consummed by HP (kWh)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    if savefig:
        fig.savefig(
            os.path.join(
                fldr_fig,'0-Annual_Energy_HeaterVsHWD.png'
                ),
            bbox_inches='tight')
    if showfig:
        plt.show()
    plt.close()
    return

#---------------------------------------
def plot_etastg_vs_SOC(
        results: pd.DataFrame,
        fldr_fig: str,
        savefig: bool = False,
        showfig: bool = False,
        ):
    
    fig, ax = plt.subplots(figsize=(9,6))
    j=0
    for location in LOCATIONS_FEW:
        i=0
        for profile_HWD in LIST_PROFILE_HWD:
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
    for HWDP in HWDP_NAMES:
        ax2.scatter([],[],c='gray',marker=mm[i],label=HWDP_NAMES[i+1])
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
                fldr_fig,'0-Eta_stg_Vs_SOC_min.png'
                ),
            bbox_inches='tight')
    if showfig:
        plt.show()
    plt.close()
    return

#---------------------------------------
def plot_AnnualEnergy_Tmains(
        results: pd.DataFrame,
        fldr_fig: str,
        savefig: bool = False,
        showfig: bool = False,
        ):
    fig, ax = plt.subplots(figsize=(9,6))
    j=0
    for location in LOCATIONS_FEW:
        i=0
        for profile_HWD in LIST_PROFILE_HWD:
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
                fldr_fig,'0-Annual_Energy_Tmains.png'
                ),
            bbox_inches='tight')
    if showfig:
        plt.show()
    plt.close()
    return

#---------------------------------------
def plot_AnnualEnergy_Tamb(
        results: pd.DataFrame,
        fldr_fig: str,
        savefig: bool = False,
        showfig: bool = False,
        ):
    fig, ax = plt.subplots(figsize=(9,6))
    j=0
    for location in LOCATIONS_FEW:
        i=0
        for profile_HWD in LIST_PROFILE_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            if profile_HWD==1:
                ax.scatter(aux.temp_amb_avg, aux.heater_power_acum,
                           marker=mm[profile_HWD],c='C'+str(j),s=100,
                           label=location)
            else:
                ax.scatter(aux.temp_amb_avg, aux.heater_power_acum,
                           marker=mm[profile_HWD], c='C'+str(j),s=50)
            i+=1
        j+=1
    
    ax.grid()
    ax.legend(loc=0,fontsize=fs)
    ax.set_xlabel('Annual average ambient temperature (C)', fontsize=fs)
    ax.set_ylabel('HP Power consumption', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    if savefig:
        fig.savefig(
            os.path.join(
                fldr_fig,'0-Annual_Energy_Tamb'+location+'.png'
                ),
            bbox_inches='tight')
    if showfig:
        plt.show()
    plt.close()
    return

#---------------------------------------
def plot_AnnualEnergy_COP(
        results: pd.DataFrame,
        fldr_fig: str,
        savefig: bool = False,
        showfig: bool = False,
        ):
    fig, ax = plt.subplots(figsize=(9,6))
    j=0
    for location in LOCATIONS_FEW:
        i=0
        for profile_HWD in LIST_PROFILE_HWD:
            aux = results[
                (results.location==location)&
                (results.profile_HWD==profile_HWD)
                ]
            if profile_HWD==1:
                ax.scatter(aux.temp_amb_avg, aux.heater_perf_avg,
                           marker=mm[profile_HWD],c='C'+str(j),s=100,
                           label=location)
            else:
                ax.scatter(aux.temp_amb_avg, aux.heater_perf_avg,
                           marker=mm[profile_HWD], c='C'+str(j),s=50)
            i+=1
        j+=1
    
    ax.grid()
    ax.legend(loc=0,fontsize=fs)
    ax.set_xlabel('Annual average ambient temperature (C)', fontsize=fs)
    ax.set_ylabel('HP Annual Average COP', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    if savefig:
        fig.savefig(
            os.path.join(
                fldr_fig,'0-Annual_COP_Tamb'+location+'.png'
                ),
            bbox_inches='tight')
    if showfig:
        plt.show()
    plt.close()
    return

#---------------------------------------
def plot_Total_Emissions_one_location(
        results: pd.DataFrame,
        fldr_fig: str,
        savefig: bool = False,
        showfig: bool = False,
        location='Sydney',
        width: float = 0.1,
        ):
    
    widths = [-2.5*width, -1.5*width, -0.5*width, 0.5*width, 1.5*width, 2.5*width]
    
    fig, ax = plt.subplots(figsize=(9,6))
    i=0
    for profile_HWD in LIST_PROFILE_HWD:
        aux = results[
            (results.location==location)&
            (results.profile_HWD==profile_HWD)
            ]
        ax.bar(aux.profile_control + widths[i], aux.emissions_total,
               width, color=f'C{i}', alpha=0.8,
               label=HWDP_NAMES[profile_HWD])
        i+=1
    
    ax.set_title(location,fontsize=fs+2)
    ax.grid()
    if location=='Sydney':
        ax.legend(bbox_to_anchor=(1.01, 0.8),fontsize=fs-2)
    
    # ax.set_ylim(1.0,2.5)
    ax.set_xticks(LIST_PROFILE_CONTROL)
    ax.set_xticklabels(CL_NAMES.values(), rotation=45)
    ax.set_xlabel( 'Type of Control Load', fontsize=fs)
    ax.set_ylabel( r'Anual accumulated Emissions (t-$CO_2$-e)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    # ax.set_ylim(-0.0002,0.0)
    if savefig:
        fig.savefig(
            os.path.join(
                fldr_fig,'0-Emissions_'+location+'.png'
                ),
            bbox_inches='tight')
    if showfig:
        plt.show()
    plt.close()
    return

#---------------------------------------
def plot_COP_diff_locations(
        results: pd.DataFrame,
        fldr_fig: str,
        savefig: bool = False,
        showfig: bool = False,
        list_location: List = LOCATIONS_FEW,
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
        ax.bar(aux.profile_control + widths[i], aux.heater_perf_avg,
               width, color=f'C{i}', alpha=0.8,
               label=location)
        
        i+=1
    
    ax.set_title('Different cities with HWDP=3',fontsize=fs+2)
    ax.grid()
    # if location=='Sydney':
    ax.legend(bbox_to_anchor=(1.01, 0.8),fontsize=fs-2)
    
    # ax.set_ylim(0.0,3.0)
    ax.set_xticks(LIST_PROFILE_CONTROL)
    ax.set_xticklabels(CL_NAMES.values(), rotation=45)
    ax.set_xlabel( 'Type of Control Load', fontsize=fs)
    ax.set_ylabel( r'Annual average COP', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    # ax.set_ylim(-0.0002,0.0)
    if savefig:
        fig.savefig(
            os.path.join(
                fldr_fig,'0-COP_all.png'
                ),
            bbox_inches='tight')
    if showfig:
        plt.show()
    plt.close()
    return

#---------------------------------------
def plot_Total_Emissions_diff_locations(
        results: pd.DataFrame,
        fldr_fig: str,
        savefig: bool = False,
        showfig: bool = False,
        list_location: List = LOCATIONS_FEW,
        profile_HWD = 3,
        width = 0.15,
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
    # if location=='Sydney':
    ax.legend(bbox_to_anchor=(1.01, 0.8),fontsize=fs-2)
    
    ax.set_ylim(0.0,3.0)
    ax.set_xticks(LIST_PROFILE_CONTROL)
    ax.set_xticklabels(CL_NAMES.values(), rotation=45)
    ax.set_xlabel( 'Type of Control Load', fontsize=fs)
    ax.set_ylabel( r'Annual accumulated Emissions (t-$CO_2$-e)', fontsize=fs)
    ax.tick_params(axis='both', which='major', labelsize=fs)
    # ax.set_ylim(-0.0002,0.0)
    if savefig:
        fig.savefig(
            os.path.join(
                fldr_fig,'0-Emissions_all.png'
                ),
            bbox_inches='tight')
    if showfig:
        plt.show()
    plt.close()
    return

#---------------------------------------
def main():
    
    RESULTS_FILE = '0-parametric_HeatPump.csv'
    RESULTS_FLDR = os.path.join(
    MAIN_DIR,
    "results",
    'parametric_HeatPump',
    )
    results = pd.read_csv(
        os.path.join( RESULTS_FLDR, RESULTS_FILE ),
        index_col=0
        )

    savefig = True
    showfig = False
    plot_storage_efficiency_bars(
        results, fldr_fig=RESULTS_FLDR, savefig=savefig,showfig=showfig
        )
    plot_heater_energy_bars(
        results, fldr_fig=RESULTS_FLDR, savefig=savefig,showfig=showfig
    )
    plot_AnnualEnergy_Tamb(
        results, fldr_fig=RESULTS_FLDR, savefig=savefig,showfig=showfig
    )
    plot_AnnualEnergy_COP(
        results, fldr_fig=RESULTS_FLDR, savefig=savefig,showfig=showfig
    )
    plot_SOC_minimum_scatter(
        results, fldr_fig=RESULTS_FLDR, savefig=savefig,showfig=showfig
    )
    plot_COP_avg_scatter(
        results, fldr_fig=RESULTS_FLDR, savefig=savefig,showfig=showfig
    )
    plot_Annual_Energy_InOut(
        results, fldr_fig=RESULTS_FLDR, savefig=savefig,showfig=showfig
    )
    plot_etastg_vs_SOC(
        results, fldr_fig=RESULTS_FLDR, savefig=savefig,showfig=showfig
    )
    plot_AnnualEnergy_Tmains(
        results, fldr_fig=RESULTS_FLDR, savefig=savefig,showfig=showfig
    )
    plot_Total_Emissions_one_location(
        results, fldr_fig=RESULTS_FLDR, savefig=savefig,showfig=showfig
    )
    plot_Total_Emissions_diff_locations(
        results, fldr_fig=RESULTS_FLDR, savefig=savefig,showfig=showfig
    )
    plot_COP_diff_locations(
        results, fldr_fig=RESULTS_FLDR, savefig=savefig,showfig=showfig
    )


#---------------------------------------
if __name__ == '__main__':
    main()