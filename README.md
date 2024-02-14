# tm_solarshift

A package for thermal simulation of Domestic Electric Water Heating (DEWH) systems. It allows to generate profiles of hot water draw (HWD), controlled load (CL), weather, and electricity consumption for a household in order to estimate 

## Installation
This is a project still under development, and therefore it is not published yet on PyPi and it is not possible to install it through pip yet. Then, to run the codes, just download the repository on your local computer, create a virtual environment to install the requirements (poetry is used in this project) and run the scripts.

In addition to these scripts, you'll need TRNSYS installed in your computer with a valid licence.

## Overview
The repository is structured in the following directories and modules:
- tm_solarshift: It is the core of the repository with the main modules (each module is a .py file):
    - general: It contains the GeneralSetup class that defines the general parameters of the simulation, and its associated functions. Additionally, it works as a catalog for the constants used in the repository.
    - profiles: It contains the functions to create, generate and load the timeseries required for the simulations. It contains functions to load the HWD profiles, the electricity profiles, the controlled load signals, the weather variables, the tariffs and the emissions timeseries.
    - devices: It contains the classes to define the technical specifications of 

### Examples


## Support

This is a "work-in-progress" repository. If you have any issue please contact directly the developer or raise an issue.


## Citation

A journal paper is in progress with some of the analysis and results obtained with this code.

## Licenses
`tm_solarshift` was created by David Saldivia as part of Solarshift project (RACE or 2030). It is licensed under MIT license.
