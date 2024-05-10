# tm_solarshift
A package for thermal simulations of Domestic Electric Water Heating (DEWH) systems as part of the project Solarshift. It allows to generate profiles of hot water draw (HWD), controlled load (CL), use different weather data, and electricity consumption for a household, to run thermal simulations of hot water tanks and estimate their thermal capacity, performance, and its utilization as thermal energy storage.

## Installation
This is a project still under development, and therefore it is not published yet on PyPi and it is not possible to install it through pip or conda yet. Then, to run the codes, just download the repository on your local computer, create a virtual environment to install the requirements and run the scripts.
In the development, `poetry` was used to handle virtual environments and dependancies. If you want to use it too, intall `poetry`, then open a terminal in the main folder and use `poetry install`.

In addition to these scripts, you'll need TRNSYS installed in your computer with a valid licence.

## Overview
The repository is structured in the following directories and modules:
- `tm_solarshift` is the core of the repository. The main modules inside are:
    - [general](tm_solarshift/general.py) contains the GeneralSetup class that defines everything in the simulations. their main attributes are `household`, `DEWH`, `solar_system`, `HWDinfo`, and `simulation`.
    - [constants](tm_solarshift/constants.py) contains the `DIRECTORY`, `DEFINITIONS`, `DEFAULT` values, `SIMULATION_IO` classes, with global constants.
    - [devices](tm_solarshift/devices.py) contains the classes to define the technical specifications of different devices in a DEWH system. So far resistive heater, heat pump, and instantaneous gas heater are included.
    - [analysis](tm_solarshift/analysis) contains modules with analyser. parametric, stochastic, and financial, are the three analyses included so far.
    - [models](tm_solarshift/models) contains the different models for pv systems, dewh, and other heater technologies. It includes `trnsys`, simple gas models, a `tank-0D` python model, and a solar thermal model. Note: in order to run the TRNSYS simulations you need to have TRNSYS installed in your computer with a valid Licence.
    - [timeseries](tm_solarshift/timeseries) contains modules to generate/load the different columns in the timeseries dataframe (ts). The main modules here are:
        - [`control`](tm_solarshift/control.py), to load control schedules from different technologies (controlled load, timers, diverters).
        - [`hwd`](tm_solarshift/hwd.py), load/generate hot water draw synthetic data from behavioural/historical input.
        - [`circuits`](tm_solarshift/circuits.py) to load timeseries of real circuits (not fully implemented yet.)
        - [`market`](tm_solarshift/market.py) to load timeseries related to the energy market, such as wholesale market data, grid emissions and retailer tariffs.
        - [`weather`](tm_solarshift/weather.py) to load environmental variables from different sources (TMY files, satellite reanalysis, etc.) It also contains functions to generate stochastic samples.
    - [external](tm_solarshift/external): contains functions to load data from external sources such as NEMOSIS, NEMED, MERRA2, etc. Soon to be deprecated (all the functions will be migrated to other existing modules).

- `examples` contains scripts with examples and typical uses of this repository.
- `data`: It contains all the data required to run the simulations. In Github this folder is empty. The required folders can be checked in `tm_solarshift.constants.DATA_DIR`.
- `projects` constains the scripts where this repository is used in actual research. It is not included in the public version.

## Examples
A simple example of how to use this package for an annual simulation can be seen here: [Simple Example](examples/simple_example.py). An example of parametric analysis can be found in [Parametric Example](examples/parametric_analysis.py).
Additionally, each module has a `main()` function with an usage sample and simple testing.

## Support
This is a "work-in-progress" repository. If you have any issue please contact directly the developer or raise an issue.

## Citation
A journal paper will be published with some of the analysis and results obtained with this code.

## Licenses
`tm_solarshift` was created by David Saldivia as part of Solarshift project (RACE or 2030). It is licensed under MIT license.
