#-------------------
def simplest_use():

    #Create a general setup instance. It contains all the settings for the simulation
    from tm_solarshift.general import GeneralSetup
    GS = GeneralSetup()

    #Create a timeseries dataframe using GS
    ts = GS.create_ts()

    #Run a thermal simulation with the default case
    (out_all, out_overall) = GS.run_thermal_simulation(ts, verbose=True)
    print(out_all)          # detailed results, DataFrame
    print(out_overall)      # overall results, Dict

    #get a sample plot
    from tm_solarshift.thermal_models import postprocessing
    postprocessing.detailed_plots(GS, out_all, save_plots_detailed=False)
    
    return None

#--------------------
def changing_household_parameters():
    
    from tm_solarshift.general import (GeneralSetup, Household, ThermalSimulation)
    from tm_solarshift.devices import (ResistiveSingle, SolarSystem)
    from tm_solarshift.hwd import HWD

    # the attributes of GS and their default objects:
    GS = GeneralSetup()
    GS.household = Household()          # Information of energy plans and control strategies
    GS.DEWH = ResistiveSingle()         # Technical specifications of heater
    GS.solar_system = SolarSystem()     # Standard PV system
    GS.HWDInfo = HWD.standard_case()    # Information of HWD behaviour
    GS.simulation = ThermalSimulation() # Information of the thermal simulation itself

    #----------------------
    # Household() contains information for the energy plans and type of control
    GS.household.tariff_type = "flat"       # used when not in CL. Options ["CL", "flat", "tou"]
    GS.household.DNSP = "Ausgrid"           # used to get the tariff rates
    GS.household.location = "Sydney"        # str for cities, int for postcodes, tuple for coordinates
    GS.household.control_type = "CL"        # Other options: ["GS", timer, diverter]
    GS.household.control_load = 1           # Ausgrid schedules
    GS.household.control_random_on = True   # add randomization to CL schedules?

    #----------------------
    #running the simulation. Note: ts is optional (if not provided is calculated using GS.create_ts())
    (out_all, out_overall) = GS.run_thermal_simulation()
    print(out_all)          # detailed results, DataFrame
    print(out_overall)      # overall results, Dict

    return None

#--------------------
def changing_DEWH_technology():
    
    from tm_solarshift.general import GeneralSetup
    # GS.DEWH must be a heater object in module tm_solarshift.devices
    # The available options are:
    from tm_solarshift.devices import (
        ResistiveSingle,
        HeatPump,
        GasHeaterInstantaneous,
        GasHeaterStorage,
        SolarThermalElecAuxiliary
    )

    GS = GeneralSetup()
    GS.DEWH = ResistiveSingle.from_model_file(model="491315")   # from catalog
    GS.DEWH = HeatPump()                                        # default

    (out_all, out_overall) = GS.run_thermal_simulation()
    print(out_all)          # detailed results, DataFrame
    print(out_overall)      # overall results, Dict

    return

#--------------------
if __name__ == "__main__":

    simplest_use()

    # changing_household_parameters()

    # changing_DEWH_technology()
