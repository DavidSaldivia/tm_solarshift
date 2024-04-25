import os
import numpy as np
import pandas as pd
from functools import cache
import tm_solarshift.devices as devices
from tm_solarshift.constants import (DIRECTORY, DEFINITIONS)
from tm_solarshift.general import GeneralSetup
from tm_solarshift.utils.units import (Variable, Water)

#Control parameters
N_NODES_MAX = 50
N_THERMOSTATS_MAX = 5
N_HEATERS_MAX = 5
ITER_MAX = 20
ITER_STATES = [
    "temp",
    "temp_prev",
    "stability_checked",
    "iterations_tank",
]

class HotWaterTank():

    def __init__(self):

        # heater
        self.nom_power = Variable(3600.0, "W")
        self.eta = Variable(1.0, "-")

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

        #component locations
        height = self.height.get_value("m")
        self.f_inlet = [0, self.height_inlet.get_value("m") / height, ]
        self.f_outlet = [0, self.height_outlet.get_value("m") / height, ]
        self.f_thermostat = [self.height_thermostat.get_value("m") / height, ]
        self.f_heater = [self.height_heater.get_value("m") / height, ]

    #Creating the states initial values
    @property
    def states(self):
        N_NODES = self.nodes
        vol = self.vol.get_value("m3")
        height = self.height.get_value("m")
        radius = (vol/np.pi/height)**0.5

        cp = self.fluid.cp.get_value("J/kg-K")
        rho = self.fluid.rho.get_value("kg/m3")

        S = pd.DataFrame(index=np.arange(self.nodes))
        S["temp_initial"] = self.temp_max.get_value("degC")
        S["temp_avg"] = self.temp_max.get_value("degC")
        S["vol"] = self.vol.get_value("m3") / self.nodes
        S["capacitance"] = S["vol"]*rho*cp

        S["area_top"] = 0.
        S["area_bottom"] = 0.
        S["area_edge"] = 2 * np.pi * radius * height / N_NODES
        S["area_cond"] = np.pi * radius**2
        S["dz"] = height / N_NODES
        S.loc[0,"area_top"] = np.pi * radius**2
        S.loc[N_NODES-1,"area_bottom"] = np.pi * radius**2

        S["stability_check"] = False
        S["iterations_tank"] = None
        S["AA"] = None
        S["BB"] = None
        return S

#----------------------------
def node_containing_components(DEWH: HotWaterTank):

    N_NODES = DEWH.nodes
    N_THERMOSTATS = len(DEWH.f_thermostat)
    N_HEATERS = len(DEWH.f_heater)
    N_PORTS = len(DEWH.f_inlet)

    #checking
    if (N_NODES<=0) or (N_THERMOSTATS<0) or (N_HEATERS<0):
        raise ValueError("Number of nodes, thermostats or heaters are not allowed.")
    
    f_inlet = DEWH.f_inlet
    f_outlet = DEWH.f_outlet
    f_thermostat = DEWH.f_thermostat
    f_heater = DEWH.f_heater
    if isinstance(f_inlet, float):
        f_inlet = [f_inlet,]
    if isinstance(f_outlet, float):
        f_outlet = [f_outlet,]
    if isinstance(f_thermostat, float):
        f_thermostat = [f_thermostat,]
    if isinstance(f_heater, float):
        f_heater = [f_heater,]

    fractions = {
        "ports_inlet" : f_inlet,
        "ports_outlet" : f_outlet,
        "thermostats" : f_thermostat,
        "heaters": f_heater,
    }
    nodes = {
        "ports_inlet" : np.zeros(N_PORTS, dtype=np.int8),
        "ports_outlet" : np.zeros(N_PORTS, dtype=np.int8),
        "thermostats" : np.zeros(N_THERMOSTATS, dtype=np.int8),
        "heaters": np.zeros(N_HEATERS, dtype=np.int8),
    }

    components = ["ports_inlet", "ports_outlet", "thermostats", "heaters"]
    for component in components:
        f_component = fractions[component]
        for j in range(len(f_component)):
            if f_component[j]>=1.0:
                nodes[component][j] = 0
                continue 
            for i in range(N_NODES):
                if (1 - (i+1)/N_NODES) <= f_component[j] < (1 - i/N_NODES):
                    nodes[component][j] = i
                    break
    return (fractions, nodes)

def load_default_values(GS):
    ts = GS.create_ts_default()
    better_names = {
        "Temp_Amb": "temp_amb",
        "Temp_Mains": "temp_mains",
        "PV_Gen": "PV_gen",
        "Import_Grid": "import_grid",
        "Import_CL": "import_CL",
        "Events": "events",
        "Wholesale_Market": "wholesale_market",
        "Intensity_Index": "intensity_index",
        "Marginal_Index": "marginal_index",
    }
    ts.rename(columns=better_names, inplace=True)
    return ts

#----------------------------
def main():

    GS = GeneralSetup()
    ts_cache = os.path.join(DIRECTORY.DIR_MAIN, "dev", "ts_cache.csv")
    if os.path.isfile(ts_cache):
        ts = pd.read_csv(ts_cache, index_col=0)
    else:
        ts = load_default_values(GS)
        ts.to_csv(ts_cache)
    row = ts.iloc[0].copy()
    row["m_HWD"] = 10.

    DEWH = HotWaterTank()

    

    #Get the Global Trnsys Simulation Variables
    # Time = inputs["TIME"]
    START = GS.simulation.START.get_value("hr")
    STOP = GS.simulation.STOP.get_value("hr")
    STEP = GS.simulation.STEP.get_value("min")

    #DEHW specifications
    #number of components
    N_NODES = DEWH.nodes
    N_THERMOSTATS = len(DEWH.f_thermostat)
    N_HEATERS = len(DEWH.f_heater)
    N_PORTS = 2 #len(DEWH.f_inlet)

    #heater
    nom_power = DEWH.nom_power.get_value("W")
    eta = DEWH.eta.get_value("-")

    #tank
    vol = DEWH.vol.get_value("m3")
    height = DEWH.height.get_value("m")
    radius = (vol/np.pi/height)**0.5

    U_top = DEWH.U.get_value("W/m2-K")
    U_edge = DEWH.U.get_value("W/m2-K")
    U_bottom = DEWH.U.get_value("W/m2-K")

    #fluid
    cp = DEWH.fluid.cp.get_value("J/kg-K")
    rho = DEWH.fluid.rho.get_value("kg/m3")
    k_th = DEWH.fluid.k.get_value("W/m-K")

    (fractions,nodes) = node_containing_components(DEWH)

    iterations_tank = [None] * N_NODES
    time = None

    #get the initial values for the nodes
    S = DEWH.states.copy()
    temp_avg_tank = S["temp_initial"].mean()
    temp_tank = S["temp_avg"]
    
    #get the input values
    temp_in = np.array([0., row["temp_mains"]])    #[port1, port2]. Values for resistive heater
    massflow_in = np.array([0., row["m_HWD"]])     #[port1, port2]. Values for resistive heater


    ports = [None,]*N_PORTS
    COLS_PORTS = ["temp_in", "massflow_in", "f_inlet", "f_outlet",
                  "temp_load_in", "mfr_load_in", "mfr_load_out",]
    for j in range(N_PORTS):
        ports[j] = pd.DataFrame(
            index = range(N_NODES),
            columns = COLS_PORTS,
        )
        ports[j]["f_outlet"] = np.where(ports[j].index == nodes["ports_outlet"][j],1,0)
        ports[j]["f_inlet"] = np.where(ports[j].index == nodes["ports_inlet"][j],1,0)
        ports[j]["temp_in"] = np.where(
            ports[j].index == nodes["ports_inlet"][j],
            temp_in[j],
            np.nan
        )
        ports[j]["massflow_in"] = np.where(
            ports[j].index == nodes["ports_inlet"][j],
            massflow_in[j],
            np.nan
        )

    temp_top_loss = row["temp_amb"]
    temp_edge_loss = row["temp_amb"]
    temp_bottom_loss = row["temp_amb"]
    
    heaters_Q_input = [nom_power] * N_HEATERS    #Assume all heaters same input (it works for 1 heater)

    #Set some initial conditions for the iterative calculations
    S["stability_check"] = False
    S["iterations_tank"] = 1
    iterations_tank_max = 1
    checking_temperatures = True
    heat_edge_loss = 0.
    heat_bottom_loss = 0.
    heat_top_loss = 0.
    heat_heaters_total = 0.
    heat_stored_tank = 0.
    heat_delivered_port = 0.
    heat_delivered_total = 0.

    #STARTING THE LOOP!!
    converge = False
    while not(converge):
        
        S["AA"] = 0.
        S["BB"] = 0.

        massflow_mains = np.array([ port["massflow_in"] * port["f_inlet"] for port in ports ])
        massflow_load_in = np.zeros((N_PORTS,N_NODES))
        massflow_load_out = np.zeros((N_PORTS,N_NODES))
        temp_load_in = np.zeros((N_PORTS,N_NODES))

        # Set the inlet temperatures and flows to each tank node from each port
        for i in range(N_PORTS):
            #from the bottom towards the outlet
            for j in reversed(range(N_NODES)):
                if j == nodes["ports_outlet"][i]:
                    break
                elif (j == N_NODES-1):
                    temp_load_in[i,j] = temp_tank[j]
                    massflow_load_in[i,j] = 0.
                    massflow_load_out[i,j] = massflow_mains[i,j]
                else:
                    temp_load_in[i,j] = temp_tank[j+1]
                    massflow_load_in[i,j] = massflow_load_out[i,j+1]
                    massflow_load_out[i,j] = massflow_mains[i,j] + massflow_load_in[i,j]
            
           # Now from the top towards the outlet
            for j in range(N_NODES):
               if (j == nodes["ports_outlet"][i]):
                    break
               elif(j==0):
                  temp_load_in[i,j] = temp_tank[j]
                  massflow_load_in[i,j] = 0.
                  massflow_load_out[i,j] = massflow_mains[i,j]
               else:
                  temp_load_in[i,j] = temp_tank[j-1]
                  massflow_load_in[i,j] = massflow_load_out[i,j-1]
                  massflow_load_out[i,j] = massflow_mains[i,j] + massflow_load_in[i,j]

        print("inside loop")
        print(temp_load_in)
        print(massflow_load_in)
        print(massflow_load_out)

        # Set the AA and BB terms for the nodal differential equation for the inlet flows
        for i in range(N_PORTS):
            for j in range(N_NODES):
               
               if (N_NODES==1):
                    S["AA"][j] = S["AA"][j] - (massflow_mains[i,j] * cp / S["capacitance"][j])
                    S["BB"][j] = S["BB"][j] + (
                        massflow_mains[i,j] * cp * temp_in[i] / S["capacitance"][j]
                    )

               elif ( j != nodes["ports_outlet"][i] ):
                    S["AA"][j] = S["AA"][j] - (massflow_load_out[i,j]*cp/S["capacitance"][j])
                    S["BB"][j] = S["BB"][j] + (
                        massflow_mains[i,j] * cp * temp_in[i]       #Check this and other ports[i]["temp_in"]
                        + massflow_load_in[i,j] * cp * temp_load_in[i,j]
                    )/S["capacitance"][j]

               else:
                    if (j==0):
                        massflow_load_out[i,j] = massflow_in[i]
                        massflow_load_in[i,j] = massflow_load_out[i,j+1]
                        
                        temp_load_in[i,j] = temp_tank[j+1]

                        S["AA"][j]=S["AA"][j] - (massflow_load_out[i,j] * cp / S["capacitance"][j])
                        S["BB"][j]=S["BB"][j] + (
                            massflow_mains[i,j] * cp * temp_in[i]
                            + massflow_load_in[i,j] * cp * temp_load_in[i,j]
                        )/S["capacitance"][j]
                
                    elif (j==N_NODES-1):
                        massflow_load_out[i,j] = massflow_in[i]
                        massflow_load_in[i,j] = massflow_load_out[i,j-1]
                        temp_load_in[i,j] = temp_tank[j-1]

                        S["AA"][j] = S["AA"][j] - (massflow_load_out[i,j] * cp / S["capacitance"][j])
                        S["BB"][j] = S["BB"][j] + (
                            massflow_mains[i,j] * cp * temp_in[i]
                            + massflow_load_in[i,j] * cp * temp_load_in[i,j]
                        )/S["capacitance"][j]

                    else:
                        massflow_load_out[i,j] = massflow_in[i]
                        massflow_load_in[i,j] = massflow_load_out[i,j-1] + massflow_load_out[i,j+1]
                    
                        if ( massflow_in[i]>0. and 
                            ( (massflow_load_out[i,j-1] + massflow_load_out[i,j+1] ) >0. )
                        ):
                            temp_load_in[i,j] = (
                                temp_tank[j-1] * massflow_load_out[i,j-1]
                                + temp_tank[j+1] * massflow_load_out[i,j+1]
                            ) / ( massflow_load_out[i,j-1] + massflow_load_out[i,j+1] )
                        else:
                            temp_load_in[i,j]=temp_tank[j]

                        S["AA"][j] = S["AA"][j] - massflow_load_out[i,j] * cp / S["capacitance"][j]
                        S["BB"][j] = S["BB"][j] + (
                            massflow_mains[i,j] * cp * temp_in[i]
                            + massflow_load_out[i,j-1] * cp * temp_tank[j-1]
                            + massflow_load_out[i,j+1] * cp * temp_tank[j+1]
                        )/S["capacitance"][j]
    

        # Set the AA and BB terms for the nodal differential equation for the auxiliary heaters
        for i in range(N_HEATERS):
            S["BB"][nodes["heaters"][i]] = (
                S["BB"][nodes["heaters"][i]] 
                + heaters_Q_input[i] / S["capacitance"][nodes["heaters"][i]]
            )

        ####################################
        #FORTRAN TRANSLATED
        #Set the AA and BB terms for the nodal differential equation for the thermal losses from the top surface
        for j in range(N_NODES):
            UA_top_surface = U_top * S["area_top"][j]
            S["AA"][j] = S["AA"][j] - UA_top_surface / S["capacitance"][j]
            S["BB"][j] = S["BB"][j] + UA_top_surface * temp_top_loss / S["capacitance"][j]

        #Set the AA and BB terms for the nodal differential equation for the thermal losses from the edge surfaces
        for j in range(N_NODES):
            UA_edges = U_edge * S["area_edge"][j]
            S["AA"][j] = S["AA"][j] - UA_edges / S["capacitance"][j]
            S["BB"][j] = S["BB"][j] + UA_edges * temp_edge_loss / S["capacitance"][j]
        
        #Set the AA and BB terms for the nodal differential equation for the thermal losses from the bottom surface
        for j in range(N_NODES):
            UA_bottom_surface = U_bottom * S["area_bottom"][j]
            S["AA"][j] = S["AA"][j] - UA_bottom_surface / S["capacitance"][j]
            S["BB"][j] = S["BB"][j] + UA_bottom_surface * temp_bottom_loss / S["capacitance"][j]
        ####################################
            
        # CONVERTED TO PYTHON
        #Set the AA and BB terms for the nodal differential equation for the thermal losses
        S["AA"] = S["AA"] - (
            U_top*S["area_top"] + U_edge*S["area_edge"] + U_bottom*S["area_bottom"]
        ) / S["capacitance"]
        S["BB"] = S["BB"] + (
            + U_top*S["area_top"]*temp_top_loss
            + U_edge*S["area_edge"]*temp_edge_loss
            + U_bottom*S["area_bottom"]*temp_bottom_loss
        ) / S["capacitance"]
        #####################################
        
        
        #Set the AA and BB terms for the nodal differential equation for conduction between nodes
        if (N_NODES > 1):
            for j in range(N_NODES):
                if (j==0):
                    S["AA"][j] = S["AA"][j] - (k_th * S["area_cond"][j] / S["dz"][j] / S["capacitance"][j])
                    S["BB"][j] = S["BB"][j] + (k_th * S["area_cond"][j] / S["dz"][j] * temp_tank[j+1] / S["capacitance"][j])
                elif (j==N_NODES-1):
                    S["AA"][j] = S["AA"][j] - (k_th * S["area_cond"][j-1] / S["dz"][j-1] / S["capacitance"][j] )
                    S["BB"][j] = S["BB"][j] + (k_th * S["area_cond"][j-1] / S["dz"][j-1] * temp_tank[j-1] / S["capacitance"][j])
                else:
                    S["AA"][j] = S["AA"][j] - (
                        k_th * S["area_cond"][j] / S["dz"][j] / S["capacitance"][j]
                        - k_th * S["area_cond"][j-1] / S["dz"][j-1] / S["capacitance"][j]
                    )
                    S["BB"][j] = S["BB"][j] + (
                        k_th * S["area_cond"][j] / S["dz"][j] * temp_tank[j+1] / S["capacitance"][j]
                        + k_th * S["area_cond"][j-1] / S["dz"][j-1] * temp_tank[j-1] / S["capacitance"][j]
                    )


        converge = True
    return

if __name__ == "__main__":
    main()
    


# !-----------------------------------------------------------------------------------------------------------------------

# !-----------------------------------------------------------------------------------------------------------------------
# !Get the Initial Values of the Dynamic Variables from the Global Storage Array
#  Do j=1,N_NODES
#     nodes_tank_temp_initial(j)=getDynamicArrayValueLastSTEP_s(j)
#     nodes_tank_temp_start(j)=getDynamicArrayValueLastSTEP_s(j)
#     nodes_tank_temp_final(j)=getDynamicArrayValueLastSTEP_s(j)
#     nodes_tank_temp_avg(j)=getDynamicArrayValueLastSTEP_s(j)
#  EndDo
# !-----------------------------------------------------------------------------------------------------------------------


# !Start the iterative calculations here - everything above this point is independent of the iterative scheme
#  200 Continue

# !Handle the single node tank case
#  If(N_NODES==1) Then
#     Do i=1,N_PORTS
#        massflow_load_in(i,1)=0.
#        massflow_load_out(i,1)=massflow_mains(i,1)
#     EndDo
#  EndIf


# !Determine the final and average tank node temperatures
#  Do j=1,N_NODES
#     If(AA(j)==0.) Then
#        nodes_tank_temp_final_New(j)=nodes_tank_temp_initial(j)+BB(j)*STEP_s
#        nodes_tank_temp_avg_New(j)=nodes_tank_temp_initial(j)+BB(j)*STEP_s/2.
#     Else
#        nodes_tank_temp_final_New(j)=(nodes_tank_temp_initial(j)+BB(j)/AA(j))*DEXP(AA(j)*STEP_s)-BB(j)/AA(j)
#        nodes_tank_temp_avg_New(j)=(nodes_tank_temp_initial(j)+BB(j)/AA(j))*(DEXP(AA(j)*STEP_s)-1.)/AA(j)/STEP_s-BB(j)/AA(j)
#     EndIf
#  EndDo

# !See If the tank node temperatures have converged
#  converged_tank=.TRUE.
#  Do j=1,N_NODES
#     If((DABS(nodes_tank_temp_avg_New(j)-nodes_tank_temp_avg(j))>conv_criteria).AND.(iterations_tank(j)<=ITER_MAX)) Then
#        converged_tank=.FALSE.
#        iterations_tank(j)=iterations_tank(j)+1
#        iterations_tank_max=MAX(iterations_tank_max,iterations_tank(j))
#     EndIf
#  EndDo
          
#  If(converged_tank) Then
#     If(iterations_tank_max>=ITER_MAX) Then
#        iteration_limit_reached_tank=.TRUE.
#     Else
#        iteration_limit_reached_tank=.FALSE.
#     EndIf

#     Do j=1,N_NODES
#        nodes_tank_temp_avg(j)=nodes_tank_temp_avg_New(j)
#        nodes_tank_temp_final(j)=nodes_tank_temp_final_New(j)
#     EndDo
#  Else
#     Do j=1,N_NODES
#        nodes_tank_temp_avg(j)=nodes_tank_temp_avg_New(j)
#        nodes_tank_temp_final(j)=nodes_tank_temp_final_New(j)
#     EndDo
         
#     GoTo 200
#  EndIf
 
# !Calculate the average temperatures
#  temp_avg_tank=0.
#  Do j=1,N_NODES
#     temp_avg_tank=temp_avg_tank+nodes_tank_temp_avg(j)/DBLE(N_NODES)
#  EndDo

# !Calculate the tank energy flows
#  Do j=1,N_NODES
#     UA_edges=U_edge*area_edges(j)
#     heat_edge_loss=heat_edge_loss+UA_edges*(nodes_tank_temp_avg(j)-temp_edge_loss)
#     UA_bottom_surface=U_bottom*area_bottom_surface(j)
#     heat_bottom_loss=heat_bottom_loss+UA_bottom_surface*(nodes_tank_temp_avg(j)-temp_bottom_loss)
#     UA_top_surface=U_top*area_top_surface(j)
#     heat_top_loss=heat_top_loss+UA_top_surface*(nodes_tank_temp_avg(j)-temp_top_loss)
#     heat_stored_tank=heat_stored_tank+nodes_capacitance(j)*(nodes_tank_temp_final(j)-nodes_tank_temp_start(j))/TimeStep
         
#     Do i=1,N_Ports
#        heat_delivered_port(i)=heat_delivered_port(i)+massflow_load_out(i,j)*cp*nodes_tank_temp_avg(j)-massflow_mains(i,j)*cp*ports_temp_in(i)-massflow_load_in(i,j)*cp*temp_load_in(i,j)
#     EndDo
#  EndDo
    
#  Do i=1,N_HEATERS
#     heat_heaters_total=heat_heaters_total+heaters_Q_input(i)
#  EndDo

#  Do i=1,N_Ports
#     heat_delivered_total=heat_delivered_total+heat_delivered_port(i)
#  EndDo

# !Calculate the energy balance errors
#  energy_balance_numerator_tank=heat_stored_tank+heat_edge_loss+heat_bottom_loss+heat_top_loss+heat_delivered_total-heat_heaters_total
#  energy_balance_denominator_tank=DABS(heat_top_loss)+DABS(heat_delivered_total)+DABS(heat_edge_loss)+DABS(heat_bottom_loss)+DABS(heat_heaters_total)
#  energy_balance_error_tank=DABS(energy_balance_numerator_tank)/DMAX1(1.0,energy_balance_denominator_tank)*100.
# !-----------------------------------------------------------------------------------------------------------------------

# !-----------------------------------------------------------------------------------------------------------------------
# !Perform an instantaneous adiabatic mixing to eliminate temperature inversions
#  5150 Continue

#  Do j=1,N_NODES-1
#     If(nodes_tank_temp_final(j)<nodes_tank_temp_final(j+1)) Goto 5165
#  EndDo

# !Update the dynamic variables
#  Do j=1,N_NODES
#     Call SetDynamicArrayValueThisIteration(j,nodes_tank_temp_final(j))
#  EndDo

#  Goto 300

#  5165 Continue

#  temp_mixed = 0.
#  capacitance_mixed = 0.
#  Do m=j,N_NODES
#     temp_mixed = temp_mixed + nodes_tank_temp_final(m)*nodes_capacitance(m)
#     capacitance_mixed = capacitance_mixed + nodes_capacitance(m)
#     If(m==N_NODES) Goto 5185
#     If(temp_mixed/capacitance_mixed>nodes_tank_temp_final(m+1)) Goto 5185
#  EndDo

#  5185 Continue
 
#  temp_mixed = temp_mixed/capacitance_mixed
      
#  Do k=j,m
#     If(AA(k)==0.) Then
#        mixing_final_factor = TimeStep/nodes_capacitance(k)
#        mixing_avg_factor = mixing_final_factor/2.
#     Else
#        mixing_final_factor=(DEXP(AA(k)*TimeStep)-1.)/AA(k)/nodes_capacitance(k)
#        mixing_avg_factor=((DEXP(AA(k)*TimeStep)-1.)/AA(k)/TimeStep-1.)/AA(k)/nodes_capacitance(k)
#     EndIf
         
#     mixing_q_adiabatic=(temp_mixed-nodes_tank_temp_final(k))/mixing_final_factor
         
#     nodes_tank_temp_final(k)=temp_mixed
#     nodes_tank_temp_avg(k)=nodes_tank_temp_avg(k)+mixing_q_adiabatic*mixing_avg_factor
#  EndDo
    
#  Goto 5150
# !-----------------------------------------------------------------------------------------------------------------------

# !-----------------------------------------------------------------------------------------------------------------------
# !Set the Outputs from this Model (#,Value)
# 300 Continue
    
#  Call setOutputValue(1,nodes_tank_temp_avg(nodes_ports_outlet(1)))
#  Call setOutputValue(2,ports_massflow_in(1))
#  Call setOutputValue(3,nodes_tank_temp_avg(nodes_ports_outlet(2)))
#  Call setOutputValue(4,ports_massflow_in(2))
#  Call setOutputValue(5,temp_avg_tank)
#  Call setOutputValue(6,heat_delivered_port(1))
#  Call setOutputValue(7,heat_delivered_port(2))
#  Call setOutputValue(8,heat_top_loss)
#  Call setOutputValue(9,heat_edge_loss)
#  Call setOutputValue(10,heat_bottom_loss)
#  Call setOutputValue(11,heat_heaters_total)
#  Call setOutputValue(12,heat_stored_tank)
#  Call setOutputValue(13,energy_balance_error_tank)

#  Do j=1,N_THERMOSTATS
#     Call setOutputValue(13+j,nodes_tank_temp_avg(nodes_thermostat(j)))
#  EndDo

#  Do j=1,N_NODES
#     Call setOutputValue(13+N_THERMOSTATS+j,nodes_tank_temp_avg(j))
#  EndDo
# !-----------------------------------------------------------------------------------------------------------------------

#  Return
#  End
