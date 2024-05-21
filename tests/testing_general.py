
from tm_solarshift.utils.units import Variable
from tm_solarshift.models.dewh import (ResistiveSingle, HeatPump)
from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)
from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary
from tm_solarshift.general import Simulation

def main():
    variable1 = Variable(12.,"m")
    variable2 = Variable(50.,"kg/s")
    sim = Simulation()
    heat_pump = HeatPump()
    
    print(variable1)
    print(variable2)
    print(sim.DEWH.nom_power.get_value("W"))

if __name__=="__main__":
    main()