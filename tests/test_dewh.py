from tm_solarshift.models.resistive_single import ResistiveSingle
from tm_solarshift.utils.units import Variable

def test_dewh_from_catalog():
    
    #assemble
    heater = ResistiveSingle.from_model_file(model="491315")

    assert type(heater.vol) == Variable
    assert type(heater.tank_thermal_cap) == Variable

    # print(heater.thermal_cap)
    # print(heater.diam)
    # print(heater.area_loss)
    # print(heater.temp_high_control)
    # print()

    # #Example of Heat Pump technical information
    # heater = HeatPump()
    # print(heater.thermal_cap)
    # print(heater.diam)
    # print(heater.area_loss)
    # print(heater.temp_high_control)
    # print()

    # #Example of Gas Heater Instantenous
    # from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)
    # heater = GasHeaterInstantaneous()
    # print(heater.nom_power)
    # print(heater.eta)
    # print(heater.vol)
    # print()

    # #Example of Gas Heater Instantenous
    # heater = GasHeaterStorage()
    # print(heater.nom_power)
    # print(heater.eta)
    # print(heater.vol)