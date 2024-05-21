#-------------------
def simplest_use():

    #Create a general setup instance. It contains all the settings for the simulation
    from tm_solarshift.general import Simulation
    sim = Simulation()

    #Create a timeseries dataframe using GS
    ts = sim.create_ts()

    #Run a thermal simulation with the default case
    (out_all, out_overall) = sim.run_thermal_simulation(ts, verbose=True)
    print(out_all)          # detailed results, DataFrame
    print(out_overall)      # overall results, dict

    #get a sample plot
    from tm_solarshift.models import postprocessing
    postprocessing.detailed_plots(sim, out_all, save_plots_detailed=False)
    
    return None

#--------------------
def changing_household_parameters():
    
    from tm_solarshift.general import (Simulation, Household, TimeSeries)
    from tm_solarshift.models.dewh import ResistiveSingle
    from tm_solarshift.models.pv_system import PVSystem
    from tm_solarshift.timeseries.hwd import HWD

    # the attributes of GS and their default objects:
    sim = Simulation()
    sim.household = Household()          # Information of energy plans and control strategies
    sim.DEWH = ResistiveSingle()         # Technical specifications of heater
    sim.pv_system = PVSystem()     # Standard PV system
    sim.HWDInfo = HWD.standard_case()    # Information of HWD behaviour
    sim.ts = TimeSeries() # Information of the thermal simulation itself

    #----------------------
    # Household() contains information for the energy plans and type of control
    sim.household.tariff_type = "tou"       # used when not in CL. Options ["CL", "flat", "tou"]
    sim.household.DNSP = "Ausgrid"           # used to get the tariff rates
    sim.household.location = "Sydney"        # str for cities, int for postcodes, tuple for coordinates
    sim.household.control_type = "CL"        # Other options: ["GS", timer, diverter]
    sim.household.control_load = 1           # Ausgrid schedules
    sim.household.control_random_on = True   # add randomization to CL schedules?

    #----------------------
    #running the sim. Note: ts is optional (if not provided is calculated using sim.create_ts())
    (out_all, out_overall) = sim.run_thermal_simulation()
    print(out_all)          # detailed results, DataFrame
    print(out_overall)      # overall results, dict

    return None

#--------------------
def changing_DEWH_technology():
    
    from tm_solarshift.general import Simulation
    # sim.DEWH must be a heater object in module tm_solarshift.devices
    # The available options are:
    from tm_solarshift.models.dewh import (
        ResistiveSingle,
        HeatPump,
        GasHeaterInstantaneous,
        GasHeaterStorage,
        SolarThermalElecAuxiliary
    )

    sim = Simulation()
    sim.DEWH = ResistiveSingle.from_model_file(model="491315")   # from catalog
    sim.DEWH = HeatPump()                                        # default

    (out_all, out_overall) = sim.run_thermal_simulation()
    print(out_all)          # detailed results, DataFrame
    print(out_overall)      # overall results, dict

    return

#--------------------
if __name__ == "__main__":

    simplest_use()

    # changing_household_parameters()

    # changing_DEWH_technology()
