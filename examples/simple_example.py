#-------------------
def simplest_use():

    #Create a general setup instance. It contains all the settings for the simulation
    from tm_solarshift.general import Simulation
    simulation = Simulation()

    #Create a timeseries dataframe using GS
    ts = simulation.create_ts()

    #Run a thermal simulation with the default case
    (out_all, out_overall) = simulation.run_thermal_simulation(ts, verbose=True)
    print(out_all)          # detailed results, DataFrame
    print(out_overall)      # overall results, dict

    #get a sample plot
    from tm_solarshift.models import postprocessing
    postprocessing.detailed_plots(simulation, out_all, save_plots_detailed=False)
    
    return None

#--------------------
def changing_household_parameters():
    
    from tm_solarshift.general import (Simulation, Household, ThermalSimulation)
    from tm_solarshift.devices import (ResistiveSingle, SolarSystem)
    from tm_solarshift.timeseries.hwd import HWD

    # the attributes of GS and their default objects:
    simulation = Simulation()
    simulation.household = Household()          # Information of energy plans and control strategies
    simulation.DEWH = ResistiveSingle()         # Technical specifications of heater
    simulation.solar_system = SolarSystem()     # Standard PV system
    simulation.HWDInfo = HWD.standard_case()    # Information of HWD behaviour
    simulation.simulation = ThermalSimulation() # Information of the thermal simulation itself

    #----------------------
    # Household() contains information for the energy plans and type of control
    simulation.household.tariff_type = "tou"       # used when not in CL. Options ["CL", "flat", "tou"]
    simulation.household.DNSP = "Ausgrid"           # used to get the tariff rates
    simulation.household.location = "Sydney"        # str for cities, int for postcodes, tuple for coordinates
    simulation.household.control_type = "CL"        # Other options: ["GS", timer, diverter]
    simulation.household.control_load = 1           # Ausgrid schedules
    simulation.household.control_random_on = True   # add randomization to CL schedules?

    #----------------------
    #running the simulation. Note: ts is optional (if not provided is calculated using simulation.create_ts())
    (out_all, out_overall) = simulation.run_thermal_simulation()
    print(out_all)          # detailed results, DataFrame
    print(out_overall)      # overall results, dict

    return None

#--------------------
def changing_DEWH_technology():
    
    from tm_solarshift.general import Simulation
    # simulation.DEWH must be a heater object in module tm_solarshift.devices
    # The available options are:
    from tm_solarshift.devices import (
        ResistiveSingle,
        HeatPump,
        GasHeaterInstantaneous,
        GasHeaterStorage,
        SolarThermalElecAuxiliary
    )

    simulation = Simulation()
    simulation.DEWH = ResistiveSingle.from_model_file(model="491315")   # from catalog
    simulation.DEWH = HeatPump()                                        # default

    (out_all, out_overall) = simulation.run_thermal_simulation()
    print(out_all)          # detailed results, DataFrame
    print(out_overall)      # overall results, dict

    return

#--------------------
if __name__ == "__main__":

    simplest_use()

    # changing_household_parameters()

    # changing_DEWH_technology()
