# tm_solarshift

A package for thermal simulations of Domestic Electric Water Heating (DEWH) systems as part of the project Solarshift. It allows to generate profiles of hot water draw (HWD), controlled load (CL), use different weather data, and electricity consumption for a household, to run thermal simulations of hot water tanks and estimate their thermal capacity, performance, and its utilization as thermal energy storage.

## Installation
This is a project still under development, and therefore it is not published yet on PyPi and it is not possible to install it through pip yet. Then, to run the codes, just download the repository on your local computer, create a virtual environment to install the requirements and run the scripts.
In the development, `poetry` was used to handle virtual environments and dependancies. If you want to use it too, intall `poetry`, then open a terminal in the main folder and use `poetry install`.

In addition to these scripts, you'll need TRNSYS installed in your computer with a valid licence.

## Overview

The repository is structured in the following directories and modules:
- `tm_solarshift` is the core of the repository. The main modules inside are:
    - [general](tm_solarshift/general.py) contains the GeneralSetup class that defines everything in the simulations. their main attributes are `household`, `DEWH`, `solar_system`, `HWDinfo`, and `simulation`.
    - [constants](tm_solarshift/constants.py) contains the `DIRECTORY` with all the global constants and utility classes.
    - [circuits](tm_solarshift/circuits.py) contains the functions to load the control load profiles into the simulations. It also contains the functions to load the solar and consumption timeseries (under development.)
    - [devices](tm_solarshift/devices.py): contains the classes to define the technical specifications of different devices in a DEWH system. So far resistive heater, heat pump, and instantaneous gas heater are included.
    - [external_data](tm_solarshift/external_data.py): contains functions to load data from external sources such as NEMOSIS, NEMED, MERRA2, etc.
    - [hwd](tm_solarshift/hwd.py) contains the function that loads/generates the hot water draw profiles.
    - [weather](tm_solarshift/weather.py) contains the function to load from the weather source files and generates random files (if needed) for the simulations.
    - [trnsys](tm_solarshift/trnsys.py): It contains the functions to run a TRNSYS simulation based on GeneralSetup and the profiles defined earlier. It also includes the postprocessing from the resulting simulation. In order to run the TRNSYS simulations you need to have TRNSYS installed in your computer with a valid Licence. If you have so, you can edit the `trnsys.TRNSYS_EXECUTABLE` string with your TRNSYS executable path.

- `uses`: It contains scripts with examples and typical uses of this repository. Scripts to run parametric simulations, events simulations, are included here. Also, plotting scripts are included.
- `data`: It contains all the data required to run the simulations. In Github this folder is empty. The required folders can be checked in `tm_solarshift.general.DATA_DIR`.
- `results`: the default folder where the different results are stored.


### Examples
A simple example of how to use this package for an annual simulation can be seen here: [Simple Example](uses/simple_example.py).
Additionally, a script for parametric runs is available [Here](uses/TL_parametric.py). Examples of parametric simulations for different tank properties, resistive heater under different conditons and heat pumps under different conditions are also available.

## Support
This is a "work-in-progress" repository. If you have any issue please contact directly the developer or raise an issue.


## Citation

A journal paper is in progress with some of the analysis and results obtained with this code.

## Licenses
`tm_solarshift` was created by David Saldivia as part of Solarshift project (RACE or 2030). It is licensed under MIT license.
