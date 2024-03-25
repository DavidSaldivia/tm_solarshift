
from tm_solarshift.general import (
    GeneralSetup,
    Household,
    ThermalSimulation
    )
from tm_solarshift.devices import (
    ResistiveSingle,
    HeatPump,
    SolarSystem,
)
from tm_solarshift.hwd import HWD

#-------------------

def main():

    #Create a general setup instance. It contains all the settings for the simulation
    GS = GeneralSetup()

    #Create a timeseries dataframe. For now, only with default values
    ts = GS.create_ts_default()

    #Run a thermal simulation with the default case
    #Because TRNSYS is the default engine, it generates two objects
    #out_all contains all the detailed results from the simulations
    #out_overall contain post-processed results
    (out_all, out_overall) = GS.run_thermal_simulation(ts)

    print(out_all)          #Detailed results, DataFrame
    print(out_overall)      #Overall results, Dict

    #If you want to get a sample plot of the results, check thermal_models/postprocessing.py
    from tm_solarshift.thermal_models import postprocessing
    postprocessing.detailed_plots(GS, out_all, save_plots_detailed=False)

    #-----------------------------------
    #You can change all the settings previous to run the simulation
    #These are the main attributes of GS, with their default value explicitely defined
    GS = GeneralSetup()
    GS.household = Household()          # Information of energy plans and control strategies
    GS.DEWH = ResistiveSingle()         # Technical specifications of heater
    GS.solar_system = SolarSystem()     # Standard PV system
    GS.HWDInfo = HWD.standard_case()    # Information of HWD behaviour
    GS.simulation = ThermalSimulation() # Information of the thermal simulation itself

    # Each device in the tm_solarshift.devices library has different ways to initialise them
    # Here a resistive heater is selected from a model catalog
    GS.DEWH = ResistiveSingle.from_model_file(model="491315")
    # Here a HeatPump is defined using default values
    GS.DEWH = HeatPump()

    #-----------------------------------
    # Household() contains information for the energy plans and type of control
    # Some useful attributes
    GS.household.location = "Sydney"        # str for cities, int for postcodes, tuple for coordinates
    GS.household.control_type = "CL"        # Other options: ["GS", timer, diverter]
    GS.household.control_load = 1           # Ausgrid schedules
    GS.household.tariff_type = "flat"       # used when not in CL. Options ["CL", "flat", "tou"]
    GS.household.DNSP = "Ausgrid"           # used to get the tariff rates

    #-----------------------------------
    #Let's rerun the simulation with these changes
    #We'll also include verbose
    ts = GS.create_ts_default()
    (out_all, out_overall) = GS.run_thermal_simulation(ts, verbose=True)
    postprocessing.detailed_plots(GS, out_all, save_plots_detailed=False)
    print(out_overall)
    return

if __name__ == "__main__":
    main()