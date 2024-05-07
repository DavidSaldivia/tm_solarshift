import numpy as np
import pandas as pd

from tm_solarshift.general import GeneralSetup
from tm_solarshift.utils.units import conversion_factor as CF
from tm_solarshift.devices import (
    GasHeaterInstantaneous,
    GasHeaterStorage,
    )

def instantaneous_fixed_eta(
        heater: GasHeaterInstantaneous,
        ts: pd.DataFrame,
        STEP_h: float = 3/60.,
        verbose: bool = False,
) -> tuple[None, dict[str, float]]:
    
    hw_flow = ts["m_HWD"]
    temp_amb_avg = ts["Temp_Amb"].mean()
    temp_mains_avg = ts["Temp_Mains"].mean()
    DAYS = len(np.unique(ts.index.date))

    kgCO2_TO_kgCH4 = 44. / 16.

    nom_power = heater.nom_power.get_value("MJ/hr")
    deltaT_rise = heater.deltaT_rise.get_value("dgrC")
    flow_water = heater.flow_water.get_value("L/min")

    #Assuming pure methane for gas
    heat_value = heater.heat_value.get_value("MJ/kg_gas")
    cp_water = heater.fluid.cp.get_value("J/kg-K")
    rho_water = heater.fluid.rho.get_value("kg/m3")
    eta = heater.eta.get_value("-")

    # #Calculations
    flow_gas = nom_power / heat_value         #[kg/hr]
    HW_energy = ((flow_water / CF("min", "s") * CF("L", "m3") )
                 * rho_water * cp_water 
                 * deltaT_rise
                 * CF("W", "MJ/hr")
                 )  #[MJ/hr]

    specific_energy = (nom_power / flow_water * CF("min", "hr") * CF("MJ", "kWh")) #[kWh/L]

    specific_emissions = (kgCO2_TO_kgCH4 
                     / (heat_value * CF("MJ", "kWh"))
                     / eta
                    ) #[kg_CO2/kWh_thermal]

    E_HWD = specific_energy * hw_flow * STEP_h                  #[kWh]

    E_HWD_acum = E_HWD.sum()                                    #[kWh]
    emissions = E_HWD * specific_emissions * CF("kg", "ton")    #[tonCO2]
    emissions_total = emissions.sum()                           #[tonCO2_annual]
    emissions_marginal = emissions.sum()                        #[tonCO2_annual]

    heater_heat_acum = E_HWD_acum / eta
    m_HWD_avg = (hw_flow * STEP_h).sum() / DAYS

    out_all = hw_flow.copy()
    out_all["eta"] = eta
    out_all["HeaterPower"] = specific_energy * hw_flow * CF("MJ", "kJ")    #[kJ/h]

    out_overall = {
        "heater_heat_acum": heater_heat_acum,
        "heater_perf_avg": eta,
        "E_HWD_acum": E_HWD_acum,
        "m_HWD_avg": m_HWD_avg,
        "temp_amb_avg": temp_amb_avg,
        "temp_mains_avg": temp_mains_avg,
        "emissions_total": emissions_total,
        "emissions_marginal": emissions_marginal,
        "solar_ratio": 0.0,
        "t_SOC0": 0.0,

        "heater_power_acum": np.nan,
        "E_losses": np.nan,
        "eta_stg": np.nan,
        "cycles_day": np.nan,
        "SOC_avg": np.nan,
        "SOC_min": np.nan,
        "SOC_025": np.nan,
        "SOC_050": np.nan,
    }

    return (out_all, out_overall)

#--------------------------------
def storage_fixed_eta(
        GS: GeneralSetup,
        ts: pd.DataFrame,
        verbose: bool = False,
) -> tuple[pd.DataFrame,dict[str, float]]:

    
    from tm_solarshift.models import (trnsys, postprocessing)
    DEWH: GasHeaterStorage = GS.DEWH
    if DEWH.__class__ == GasHeaterStorage:
        kgCO2_TO_kgCH4 = 44. / 16. #Assuming pure methane for gas
        heat_value = DEWH.heat_value.get_value("MJ/kg_gas")
        eta = GS.DEWH.eta.get_value("-")
    else:
        raise ValueError("DEWH type is not compatible with this function.")

    out_all = trnsys.run_simulation(GS, ts, verbose=verbose)
    out_overall = postprocessing.annual_postproc(GS, ts, out_all)
    sp_emissions = (kgCO2_TO_kgCH4 / (heat_value * CF("MJ", "kWh")) / eta ) #[kg_CO2/kWh_thermal]

    emissions_total = out_overall["heater_heat_acum"] * sp_emissions * CF("kg", "ton")    #[tonCO2_annual]
    emissions_marginal = emissions_total
    
    out_overall["emissions_total"] = emissions_total
    out_overall["emissions_marginal"] = emissions_marginal
    out_overall["solar_ratio"] = 0.0

    return (out_all, out_overall)