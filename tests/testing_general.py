
from tm_solarshift.devices import (
    Variable,
    ResistiveSingle,
    HeatPump)
from tm_solarshift.general import Simulation

def main():
    variable1 = Variable(12.,"m")
    variable2 = Variable(50.,"kg/s")
    general_setup = Simulation()
    heat_pump = HeatPump()
    
    print(variable1)
    print(variable2)
    print(general_setup.DEWH.nom_power.get_value("W"))

if __name__=="__main__":
    main()