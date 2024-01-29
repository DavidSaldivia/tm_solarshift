import os
from typing import Dict, Optional, List, Any

import tm_solarshift.profiles as profiles
from tm_solarshift.general import (GeneralSetup, DATA_DIR)
from tm_solarshift.devices import (GasHeaterInstantaneous, CONV)

def tm_state_heater_gas(
        heater_spec: Any = GasHeaterInstantaneous(),
        HW_daily_cons: float = 200.,
        HW_annual_energy: float = 2000.,
) -> dict:

    MJ_TO_kWh = CONV["MJ_to_kWh"]
    MIN_TO_SEC = CONV["min_to_s"]

    nom_power = heater_spec.nom_power.get_value("MJ/hr")
    deltaT_rise = heater_spec.deltaT_rise.get_value("dgrC")
    flow_water = heater_spec.flow_water.get_value("L/min")

    #Assuming pure methane for gas
    heat_value = heater_spec.heat_value.get_value("MJ/kg_gas")
    kgCO2_to_kgCH4 = 44. / 16.          

    cp_water = heater_spec.fluid.cp.get_value("J/kg-K")
    rho_water = heater_spec.fluid.rho.get_value("kg/m3")

    #Calculations
    flow_gas = nom_power / heat_value         #[kg/hr]
    HW_energy = ((flow_water * MIN_TO_SEC) 
                 * rho_water * cp_water 
                 * deltaT_rise
                 / 1000.
                 )  #[MJ/hr]

    eta = HW_energy / nom_power #[-]
    specific_energy = nom_power / (flow_water*60.) * MJ_TO_kWh #[kWh/L]

    emissions_CO2 = ( kgCO2_to_kgCH4 
                     / (heat_value * MJ_TO_kWh)
                     / eta
                    ) #[kg_CO2/kWh_thermal]

    daily_energy = specific_energy * HW_daily_cons #[kWh]
    annual_emissions = HW_annual_energy * emissions_CO2/1000. #[tonCO2/year]

    output = {
        "flow_gas" : flow_gas,
        "HW_energy" : HW_energy,
        "eta" : eta,
        "specific_energy" : specific_energy,
        "emissions_CO2" : emissions_CO2,
        "daily_energy" : daily_energy,
        "annual_emissions" : annual_emissions,
    }
    return output

def main():

    # Defining default parameters
    general_setup = GeneralSetup()
    general_setup.DEWH = GasHeaterInstantaneous()

    timeseries = profiles.new_profile(general_setup)
    
    #Hot water draw daily distribution
    HWD_daily_dist = profiles.HWD_daily_distribution(
        general_setup, 
        timeseries
    )
    HWD_generator_method = 'events'
    event_probs = profiles.events_file(
        file_name = os.path.join(DATA_DIR["samples"], "HWD_events.xlsx",),
        sheet_name="Custom"
        )
    timeseries = profiles.HWDP_generator(
            timeseries,
            method = HWD_generator_method,
            HWD_daily_dist = HWD_daily_dist,
            HWD_hourly_dist = general_setup.profile_HWD,
            event_probs = event_probs,
        )
    
    heater = general_setup.DEWH
    output = heater.run_simple_thermal_model(timeseries["m_HWD"])
    
    print(output)
    print(heater.nom_power)
    return


if __name__=="__main__":
    main()
    
