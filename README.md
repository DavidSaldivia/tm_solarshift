# tm_solarshift
A package for thermal simulations of Domestic Electric Water Heating (DEWH) systems as part of the project Solarshift. It allows to generate profiles of hot water draw (HWD), controlled load (CL), use different weather data, and electricity consumption for a household, to run thermal simulations of hot water tanks and estimate their thermal capacity, performance, and its utilization as thermal energy storage.

## Installation
For the moment, just download the repository on your local computer, create a virtual environment, and install the requirements.
`poetry` is used to handle dependancies. Open a terminal in the main folder and use `poetry install`.

In addition, to run thermal simulations, you'll need TRNSYS installed in your computer with a valid licence.


## Examples
A simple example of how to use this package for an annual simulation can be seen here: [Simple Example](examples/simple_example.py). An example of parametric analysis can be found in [Parametric Example](examples/parametric_analysis.py).
Additionally, each module has a `main()` function with an usage sample and simple testing.

## Overview
The repository is structured in the following directories and modules:
- `tm_solarshift` is the core of the repository. The main modules inside are:
    - [general](tm_solarshift/general.py) contains the Simulation class that defines everything in the simulations. their main attributes are `household`, `DEWH`, `solar_system`, `HWDinfo`, and `simulation`.
    - [constants](tm_solarshift/constants.py) contains the `DIRECTORY`, `DEFINITIONS`, `DEFAULT` values, `SIMULATION_IO` classes, with global constants.
    - [devices](tm_solarshift/models.py) contains the classes to define the technical specifications of different devices in a DEWH system. Five different technologies are implemented. 
    - [analysis](tm_solarshift/analysis) contains modules with analyser. parametric, stochastic, and financial, are the three analyses included so far.
    - [timeseries](tm_solarshift/timeseries) contains modules to generate/load the different columns in the timeseries dataframe (ts). The main modules are [`control`](tm_solarshift/control.py), [`hwd`](tm_solarshift/hwd.py), [`circuits`](tm_solarshift/circuits.py), [`market`](tm_solarshift/market.py), and [`weather`](tm_solarshift/weather.py).

- `examples` contains scripts with examples and typical uses of this repository.
- `data`: It contains all the data required to run the simulations. In Github this folder is empty. The required folders can be checked in `tm_solarshift.constants.DATA_DIR`.
- `projects` constains the scripts where this repository is used in actual research. It is not included in the public version.

 ## Documentation
Check the documentation!

## Support
This is a "work-in-progress" repository. If you have any problem please contact directly the developer or raise an issue.

## Citation
A journal paper is under development with some of the analysis and results obtained with this code.

## Licenses
`tm_solarshift` was created by David Saldivia as part of Solarshift project (RACE or 2030). It is licensed under MIT license.
