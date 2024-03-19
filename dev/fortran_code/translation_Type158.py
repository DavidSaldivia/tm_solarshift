"""
Translation of Type158.f90 (Cylindrical Storage Tank) available in TRNSYS's Types catalog.
This is an own manual translation of the code.
From the FORTRAN's file only the numerical method was translated.
The other sections (see below) are build from scratch to meet the original project requirements.

The goal of the translation is to have a full-python module to simulate a hot water tank for domestic use.
This was developed as part of tm_solarshift repository.

The module is divided in four sections:
    - Preparation and error checking (built from scratch)
    - Precalculations (adapted from Type158.f90 to own requirements)
    - Iterative Loop (translated from Type158.f90)
    - Final calculations and correct temperature inversion (adapted from Type158.f90 to own requirements)

"""

import os
import numpy as np
import pandas as pd
from typing import List, Any, Dict
import tm_solarshift.devices as devices
from tm_solarshift.general import GeneralSetup
from tm_solarshift.units import (Variable, Water)


DIR_PROJECT = os.path.dirname(os.path.abspath(__file__))
N_NODES_MAX = 50
N_THERMOSTAT_MAX = 5
N_HEATERS_MAX = 5


class HotWaterTank():

    def __init__(self):

        # tank
        self.vol = Variable(0.315,"m3")
        self.height = Variable(1.45, "m")
        self.height_inlet = Variable(0.113, "m")
        self.height_outlet = Variable(1.317, "m")
        self.height_heater = Variable(0.103, "m")
        self.height_thermostat = Variable(0.103, "m")
        self.U = Variable(0.9, "W/m2-K")

        self.nodes = 10
        self.temps_ini = 3
        self.fluid = Water()

        # control
        self.temp_max = Variable(65.0, "degC")  #Maximum temperature in the tank
        self.temp_deadband = Variable(10.0, "degC") # Dead band for max temp control
        self.temp_min = Variable(45.0, "degC")  # Minimum temperature in the tank
        self.temp_consump = Variable(45.0, "degC") #Consumption temperature

        self.states = pd.DataFrame(index=np.arange(self.nodes), columns = ITER_STATES)

    
    def run_thermal_model(
            self,
            ts: pd.DataFrame = None,
    ) -> pd.DataFrame:
        
        output = pd.DataFrame(index=ts.index, columns = COLS_OUTPUT)
        return output


N_NODES = 10
N_THERMOSTATS = 2
N_HEATERS = 1
N_PORTS = 2

ITER_MAX = 20
ITER_TANK_MAX = 1
COLS_OUTPUT = [
    "temp_avg",
    "SOC",
]
ITER_STATES = [
    "stability_checked",
    "iterations_tank",
]
N_PORTS = 2

nodes_ports_inlet = np.zeros(N_PORTS)
nodes_ports_OUTlet = np.zeros(N_PORTS)
nodes_thermostats = np.zeros(N_THERMOSTATS)
nodes_heaters = np.zeros(N_HEATERS)
iterations_tank = np.zeros(N_NODES)

timestep = 0
convergence_criteria = False

stability_checked = [False]
checking_temperature = True
converged_tank = False
iteration_limit_reached_tank = False

DEWH = HotWaterTank()

vol = DEWH.vol.get_value("m3")
height = DEWH.height.get_value("m")
U_top = DEWH.U.get_value("W/m2-K")
U_edge = DEWH.U.get_value("W/m2-K")
U_bottom = DEWH.U.get_value("W/m2-K")
cp = DEWH.fluid.cp.get_value("J/kg-K")
rho = DEWH.fluid.rho.get_value("kg/m3")
k = DEWH.fluid.k.get_value("W/m-K")

f_inlet = DEWH.height_inlet.get_value("m") / height
f_outlet = DEWH.height_outlet.get_value("m") / height
f_thermostat = DEWH.height_thermostat.get_value("m") / height
f_heater = DEWH.height_heater.get_value("m") / height

#  Implicit None 
#  Integer N_Nodes_Max,N_Thermostats_Max,N_AuxLocations_Max
#  Parameter (N_Nodes_Max=50,N_Thermostats_Max=5,N_AuxLocations_Max=5)
#  Integer i,j,k,m,N_Nodes,N_Thermostats,N_AuxLocations,Node_Outlet(2),Node_Thermostat(N_Thermostats_Max),Node_Inlet(2), &
#     Node_Auxiliary(N_AuxLocations_Max),Iterations_Max,Iterations_Tank_Max,N_Ports,Iterations_Tank(N_Nodes_Max)
Time,Timestep,StartTime,StopTime,ConvergenceCriteria
Volume_Tank,Height_Tank,U_Top,U_Edge,U_Bottom, SpecificHeat_TankFluid,Density_TankFluid,Conductivity_TankFluid,
Radius_Tank,
UA_topSurface,UA_Edges,UA_BottomSurface,
FracHeight_Inlet1,FracHeight_Outlet1,FracHeight_Inlet2, FracHeight_Outlet2,FracHeight_Tstat(N_Thermostats_Max),FracHeight_Aux(N_AuxLocations_Max),
Averagefactor_Mixing, Q_AdiabaticMixing,
Tinitial_TankNode(N_Nodes_Max),Taverage_TankNode(N_Nodes_Max),Tfinal_TankNode(N_Nodes_Max),
Mdot_Flow_in(2), T_Flow_in(2)
Q_Delivered_Total, Taverage_Tank, Q_Delivered_Port(2),
Q_TopLoss,Q_EdgeLoss,Q_BottomLoss, T_TopLoss, T_EdgeLoss, T_BottomLoss,
Q_Auxiliary_Total,Q_AuxiliaryInput(N_AuxLocations_Max)
Q_Stored_Tank, EnergyBalance_Error_Tank,
Fraction_Inlet(2,N_Nodes_Max), Frac_Now,
Volume_TankNode(N_Nodes_Max),
Area_TopSurface(N_Nodes_Max), Area_BottomSurface(N_Nodes_Max),Area_Edges(N_Nodes_Max),
ConductionArea(N_Nodes_Max),L_Conduction(N_Nodes_Max),
Capacitance_TankNode(N_Nodes_Max),
Tstart_TankNode(N_Nodes_Max),
AA(N_Nodes_Max),BB(N_Nodes_Max),
Mdot_Mains(2,N_Nodes_Max), T_Load_In(2,N_Nodes_Max),Mdot_Load_In(2,N_Nodes_Max),Mdot_Load_Out(2,N_Nodes_Max)
Tfinal_TankNode_New(N_Nodes_Max),Taverage_TankNode_New(N_Nodes_Max),
EnergyBalance_Numerator_Tank,EnergyBalance_Denominator_Tank,
T_Mixed,Capacitance_Mixed,Finalfactor_Mixing

# StabilityChecked(N_Nodes_Max),CheckingTemperatures,Converged_Tank,IterationLimitReached_Tank
#  Data Pi/3.14159265358979/,ConvergenceCriteria/0.0001/


def first_call_calculations(
        tank: HotWaterTank,
) -> None:
    
    N_PARAMS_MIN = 15
    N_INPUT_MIN = 7
    N_OUTPUT_MIN = 13

    N_PARAMETERS = 15 + N_THERMOSTATS + N_HEATERS
    N_INPUT = N_INPUT_MIN + N_HEATERS
    N_OUTPUT = N_OUTPUT_MIN + N_THERMOSTATS + N_NODES

    ITERATION_MODE = 1

    return None

def preparation_error_checking(
        tank: HotWaterTank,
) -> None:
    

    return None

#-----------------------
def precalculations(
        tank: HotWaterTank,
) -> None:
    return None


#-----------------------
def iterative_loop(
        tank: HotWaterTank,
        input: pd.Series,
) -> None:
    
    S = tank.states

    mfr_mains_in = input["mfr_mains_in"]
    temp_mains_in = input["temp_mains_in"]

    #Indicate that the temperatures have not been checked for stability
    S["stability_checked"] = False
    S["iterations_tank"] = 1

    #Values that should be defined the first time the model is called
    ports_inlet_fraction = np.zeros((N_PORTS, N_NODES))
    ports_massflow_in = np.zeros(N_PORTS)
    ports_massflow_in[1] = mfr_mains_in
    ports_inlet_fraction = np.loadtxt(
        os.path.join(DIR_PROJECT,"precalc_values","ports_inlet_fraction.csv"),
        delimiter=",",
        dtype=float
    )
    #Set some initial conditions for the iterative calculations
    
    iterations_tank_max = 1
    checking_temperatures = True
    heat_loss_edge = 0.
    heat_loss_bottom = 0.
    heat_loss_top = 0.
    heat_auxiliary_total = 0.
    heat_stored_tank = 0.

    heat_delivered_port = 0.
    heat_delivered_total = 0.

    ##############
    # 200 Continue
    ##############

    # Reset the differential equation terms AA and BB where  dT/dt=AA*T+BB
    S["AA"] = 0
    S["BB"] = 0

    # Set the flow rate for each node from each port
    tank_massflow_in = ports_massflow_in[:, None] * ports_inlet_fraction


    pass
    return None


#-----------------------
def temperature_inversion_check(
        heater: HotWaterTank,
) -> None:
    
    pass
    return None

#-----------------------
def generate_output(
        heater: HotWaterTank,
) -> None:
    
    pass
    return None



def main():

    # GS = GeneralSetup()
    # ts = GS.create_ts_default()
    tank = HotWaterTank()

    input = {
        "m_hw_in" : Variable(10., "kg/s"),
        "T_hw_in" : Variable(25., "degC"),
    }
    iterative_loop(tank, input)

    return

if __name__ == "__main__":
    main()


