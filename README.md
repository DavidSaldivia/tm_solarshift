# tm_solarshift

A package for thermal simulation of Domestic Electric Water Heating (DEWH) systems. It allows to generate profiles of hot water draw (HWD), controlled load (CL), weather, and electricity consumption for a household in order to estimate 

## Installation
This is a project still under development, and therefore it is not published yet on PyPi and it is not possible to install it through pip yet. Then, to run the codes, just download the repository on your local computer, create a virtual environment to install the requirements and run the scripts.
In the development, `poetry` was used to handle virtual environments and dependancies. If you want to use it too, intall `poetry`, then open a terminal in the main folder and use `poetry install`.

In addition to these scripts, you'll need TRNSYS installed in your computer with a valid licence.

## Overview

The repository is structured in the following directories and modules:
- tm_solarshift: It is the core of the repository with the main modules (each module is a .py file):
    - general: It contains the GeneralSetup class that defines the general parameters of the simulation, and its associated functions. Additionally, it works as a catalog for the constants used in the repository.
    - profiles: It contains the functions to create, generate and load the timeseries required for the simulations. It contains functions to load the HWD profiles, the electricity profiles, the controlled load signals, the weather variables, the tariffs and the emissions timeseries.
    - devices: It contains the classes to define the technical specifications of different devices in a DEWH system. So far resistive heater, heat pump, and instantaneous gas heater are included.
    - trnsys: It contains the functions to run a TRNSYS simulation based on GeneralSetup and the profiles defined earlier. It also includes the postprocessing from the resulting simulation. In order to run the TRNSYS simulations you need to have TRNSYS installed in your computer with a valid Licence. If you have so, you can edit the `trnsys.TRNSYS_EXECUTABLE` string with your TRNSYS executable path.

- uses: It contains scripts with examples and typical uses of this repository. Scripts to run parametric simulations, events simulations, are included here. Also, plotting scripts are included.
- data: It contains all the data required to run the simulations. In Github this folder is empty. The required folders can be checked in `tm_solarshift.general.DATA_DIR`.
- results: the default folder where the different results are stored.


### Examples
A simple example of how to use this package for an annual simulation can be seen here: [Simple Example](uses/simple_example.py).
Additionally, a script for parametric runs is available [Here](uses/TL_parametric.py). Examples of parametric simulations for different tank properties, resistive heater under different conditons and heat pumps under different conditions are also available.

## Support

This is a "work-in-progress" repository. If you have any issue please contact directly the developer or raise an issue.


## Citation

A journal paper is in progress with some of the analysis and results obtained with this code.

## Licenses
`tm_solarshift` was created by David Saldivia as part of Solarshift project (RACE or 2030). It is licensed under MIT license.
