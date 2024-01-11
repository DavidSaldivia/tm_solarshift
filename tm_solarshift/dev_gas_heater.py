from typing import Dict, Optional, List, Any

from tm_solarshift.utils.general import Variable
from tm_solarshift.utils.general import CONV
from tm_solarshift.utils.devices import GasHeaterInstantaneous


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

    cp_water = heater_spec.cp.value
    rho_water = heater_spec.rho.value

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


if __name__=="__main__":
    
    heater = GasHeaterInstantaneous()
    output = tm_state_heater_gas(heater)

    print(output["eta"])
    print(output["daily_energy"])
    print(output["emissions_CO2"])
    print(output["annual_emissions"])
