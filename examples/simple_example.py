#-------------------
def simplest_use():

    #Create a general setup instance. It contains all the settings for the simulation
    from tm_solarshift.general import Simulation
    sim = Simulation()

    #Run a thermal simulation with the default case
    sim.run_simulation()
    df_tm = sim.out["df_tm"]
    overall_tm = sim.out["overall_tm"]

    print(df_tm)          # detailed results, DataFrame
    print(overall_tm)      # overall results, dict

    #get a sample plot
    # from tm_solarshift.models import postprocessing
    # postprocessing.detailed_plots(sim, df_tm, save_plots_detailed=False)
    
    return None

#--------------------
def changing_household_parameters():
    
    from tm_solarshift.general import (Simulation, Household)
    from tm_solarshift.models.dewh import ResistiveSingle
    from tm_solarshift.models.pv_system import PVSystem
    from tm_solarshift.timeseries.hwd import HWD

    # the attributes of GS and their default objects:
    sim = Simulation()
    sim.household = Household()          # Information of energy plans and control strategies
    sim.DEWH = ResistiveSingle()         # Technical specifications of heater
    sim.pv_system = PVSystem()     # Standard PV system
    sim.HWDInfo = HWD.standard_case()    # Information of HWD behaviour

    # Household() contains information for the energy plans and type of control
    sim.household.tariff_type = "tou"       # used when not in CL. Options ["CL", "flat", "tou"]
    sim.household.location = "Sydney"       # str for cities, int for postcodes, tuple for coordinates
    sim.household.control_type = "CL1"      # Other options: ["GS", timer, diverter]
    sim.household.control_random_on = True  # add randomization to CL schedules?

    #Run the simulation
    sim.run_simulation()
    df_tm = sim.out["df_tm"]
    overall_tm = sim.out["overall_tm"]

    print(df_tm)          # detailed results, DataFrame
    print(overall_tm)      # overall results, dict

    return None

#--------------------
def changing_DEWH_technology():
    
    from tm_solarshift.general import Simulation
    # sim.DEWH must be a heater object in module tm_solarshift.devices
    # The available options are:
    from tm_solarshift.models.dewh import (ResistiveSingle, HeatPump)
    from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)
    from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary

    sim = Simulation()
    sim.DEWH = ResistiveSingle.from_model_file(model="491315")   # from catalog file
    sim.DEWH = HeatPump()                                        # default

    #Run the simulation
    sim.run_simulation()
    df_tm = sim.out["df_tm"]
    overall_tm = sim.out["overall_tm"]

    print(df_tm)          # detailed results, DataFrame
    print(overall_tm)      # overall results, dict


    return

#--------------------
if __name__ == "__main__":

    # simplest_use()

    changing_household_parameters()

    changing_DEWH_technology()
