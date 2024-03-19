 Subroutine Type158

!-----------------------------------------------------------------------------------------------------------------------
! Description:  This subroutine models a vertical cylindrical storage tank. This routine solves the coupled differential 
! equations imposed by considering the mass of the fluid in the storage tank and the mass of the fluid in the heat exchanger.
!
!   00.00.2015 - AMP : initial coding
!   10.24.2016 - DEB : removed two redundant error checks and corrected the error check on the number of thermostats and  
!                       number of aux energy flows so that they can be set to zero. 
!   10.00.2018 - TPM : fixed an error where conduction between nodes occurred with only one node
!   04.29.2019 - JWT : moved the adiabatic mixing section after the energy balances but before the outputs
!   02.2023    - JWT : Fixed a bug that caused the energy balance error to be reported incorrectly (doesn't affect results)
!-----------------------------------------------------------------------------------------------------------------------
! Copyright   2023 Thermal Energy System Specialists LLC. All rights reserved.  
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
 Use TrnsysConstants
 Use TrnsysFunctions
!DEC$Attributes DLLexport :: Type158
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
 Implicit None 
 Integer N_NODES_MAX,N_THERMOSTATS_MAX,N_HEATERS_MAX
 Parameter (N_NODES_MAX=50,N_THERMOSTATS_MAX=5,N_HEATERS_MAX=5)
 
 Integer i,j,k,m, N_NODES, N_THERMOSTATS, N_HEATERS, nodes_ports_outlet(2), nodes_thermostat(N_THERMOSTATS_MAX), nodes_ports_inlet(2), &
    nodes_heaters(N_HEATERS_MAX),ITER_MAX,iterations_tank_max,N_PORTS,iterations_tank(N_NODES_MAX)
 
Double Precision Time,STEP_s,StartTime,StopTime,Pi,&
    conv_criteria, vol, height, U_top, U_edge, U_bottom, cp, rho, thermal_cond, &
    f_inlet_1, f_outlet_1, f_inlet_2, f_outlet_2, f_thermostat(N_THERMOSTATS_MAX), f_heater(N_HEATERS_MAX), &
    mixing_avg_factor, mixing_q_adiabatic, &

    nodes_tank_temp_initial(N_NODES_MAX),nodes_tank_temp_avg(N_NODES_MAX),nodes_tank_temp_final(N_NODES_MAX), &
    ports_massflow_in(2),heat_delivered_total,temp_avg_tank,heat_delivered_port(2),heat_top_loss,heat_edge_loss,heat_bottom_loss,heat_heaters_total, &
    heat_stored_tank,energy_balance_error_tank,ports_temp_in(2),temp_top_loss,temp_edge_loss,temp_bottom_loss,heaters_Q_input(N_HEATERS_MAX), &
    ports_f_inlet(2,N_NODES_MAX),f_now,nodes_vol(N_NODES_MAX),tank_radius,area_top_surface(N_NODES_MAX), &
    area_bottom_surface(N_NODES_MAX),area_edges(N_NODES_MAX),area_conduction(N_NODES_MAX),length_conduction(N_NODES_MAX), &
    nodes_capacitance(N_NODES_MAX),nodes_tank_temp_start(N_NODES_MAX),AA(N_NODES_MAX),BB(N_NODES_MAX),massflow_mains(2,N_NODES_MAX), &
    temp_load_in(2,N_NODES_MAX),massflow_load_in(2,N_NODES_MAX),massflow_load_out(2,N_NODES_MAX),UA_top_surface,UA_edges,UA_bottom_surface, &
    nodes_tank_temp_final_New(N_NODES_MAX),nodes_tank_temp_avg_New(N_NODES_MAX),energy_balance_numerator_tank,energy_balance_denominator_tank, &
    temp_mixed,capacitance_mixed,mixing_final_factor
 Logical stability_checked(N_NODES_MAX),checking_temperatures,converged_tank,iteration_limit_reached_tank
 Data Pi/3.14159265358979/,conv_criteria/0.0001/
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Get the Global Trnsys Simulation Variables
 Time=getSimulationTime()
 StartTime=getSimulationStartTime()
 StopTime=getSimulationStopTime()
 TimeStep=getSimulationTimeStep()
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Set the Version Number for This Type
 If(getIsVersionSigningTime()) Then
    Call SetTypeVersion(17)
    Return
 EndIf
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Do Any Last Call Manipulations Here
 If(getIsLastCallofSimulation()) Then
    Return
 EndIf
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Perform Any "After Convergence" Manipulations That May Be Required at the End of Each STEP_s
 If(getIsEndofSTEP_s()) Then
     !Update SSR variables
     If (getIsIncludedInSSR()) Then
       Call updateReportIntegral(1,getOutputValue(6)) !Energy Delivered Port 1
       Call updateReportIntegral(2,getOutputValue(7)) !Energy Delivered Port 2
       Call updateReportIntegral(3,getOutputValue(11)) !Auxiliary Energy
       Call updateReportIntegral(4,getOutputValue(8)+getOutputValue(9)+getOutputValue(10)) !Thermal Losses
       Call updateReportMinMax(1,getOutputValue(1)) !Outlet Temperature Port 1
       Call updateReportMinMax(2,getOutputValue(3)) !Outlet Temperature Port 2
       Call updateReportMinMax(3,getOutputValue(5)) !Average Tank Temperature
     EndIf 

    Return
 EndIf
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Do All of the "Very First Call of the Simulation Manipulations" Here
 If(getIsFirstCallofSimulation()) Then
 
   !Get the critical parameters and check them
    N_NODES=JFIX(getParameterValue(3)+0.1)
    N_THERMOSTATS=JFIX(getParameterValue(14)+0.1)
    N_HEATERS=JFIX(getParameterValue(15+N_THERMOSTATS)+0.1)

    If (N_NODES<=0) Call FoundBadParameter(3,'Fatal','The number of isothermal tank nodes must be greater than zero.')
    If (N_NODES>N_NODES_MAX) Call FoundBadParameter(3,'Fatal','The number of isothermal tank nodes supplied is greater than that currently allowed by the source code.')
    If (N_THERMOSTATS<0) Call FoundBadParameter(14,'Fatal','The number of thermostats must be greater than or equal to zero.')
    If (N_HEATERS<0) Call FoundBadParameter(15+N_THERMOSTATS,'Fatal','The number of auxiliary heat inputs must be greater than or equal to zero.')
    If (ErrorFound()) Return

    Call SetNumberofParameters(15+N_THERMOSTATS+N_HEATERS) 
    Call SetNumberofInputs(7+N_HEATERS) 
    Call SetNumberofDerivatives(N_NODES) 
    Call SetNumberofOutputs(13+N_THERMOSTATS+N_NODES) 
    Call SetIterationMode(1) 
    Call SetNumberStoredVariables(0,N_NODES) 
    Call SetNumberofDiscreteControls(0) 

!  Set the Correct Input and Output Variable Types
    Call SetInputUnits(1,'TE1')
    Call SetInputUnits(2,'MF1')
    Call SetInputUnits(3,'TE1')
    Call SetInputUnits(4,'MF1')
    Call SetInputUnits(5,'TE1')
    Call SetInputUnits(6,'TE1')
    Call SetInputUnits(7,'TE1')
    
    Do j=1,N_HEATERS
       Call SetInputUnits(7+j,'PW1')
    EndDo
    
    Call SetOutputUnits(1,'TE1')
    Call SetOutputUnits(2,'MF1')
    Call SetOutputUnits(3,'TE1')
    Call SetOutputUnits(4,'MF1')
    Call SetOutputUnits(5,'TE1')
    Call SetOutputUnits(6,'PW1')
    Call SetOutputUnits(7,'PW1')
    Call SetOutputUnits(8,'PW1')
    Call SetOutputUnits(9,'PW1')
    Call SetOutputUnits(10,'PW1')
    Call SetOutputUnits(11,'PW1')
    Call SetOutputUnits(12,'PW1')
    Call SetOutputUnits(13,'PC1')
    
    Do j=1,N_THERMOSTATS
       Call SetOutputUnits(13+j,'TE1')
    EndDo

    Do j=1,N_NODES
       Call SetOutputUnits(13+N_THERMOSTATS+j,'TE1')
    EndDo

    ! Set up this Type's entry in the SSR
    If (getIsIncludedInSSR()) Then
       Call setNumberOfReportVariables(4,3,4,0) !(nInt,nMinMax,nVals,nText)
    EndIf 

    Return

 EndIf
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Do All of the First STEP_s Manipulations Here - There Are No Iterations at the Intial Time
 If (getIsStartTime()) Then
      
   !Read in the Values of the Parameters from the Input File and Check for Problems
    vol = getParameterValue(1)
    If (vol<=0.) Call FoundBadParameter(1,'Fatal','The tank volume must be greater than zero.')

    height = getParameterValue(2)
    If (height<=0.) Call FoundBadParameter(2,'Fatal','The height of the tank must be greater than zero.')

    N_NODES=JFIX(getParameterValue(3)+0.1)
    If (N_NODES<=0) Call FoundBadParameter(3,'Fatal','The number of isothermal tank nodes must be greater than zero.')

    U_top = getParameterValue(4)
    If (U_top<0.) Call FoundBadParameter(4,'Fatal','The heat loss coefficient for the tank top surface must be greater than or equal to zero.')

    U_edge = getParameterValue(5)
    If (U_edge<0.) Call FoundBadParameter(5,'Fatal','The heat loss coefficient for the tank edges must be greater than or equal to zero.')

    U_bottom = getParameterValue(6)
    If (U_bottom<0.) Call FoundBadParameter(6,'Fatal','The heat loss coefficient for the tank bottom surface must be greater than or equal to zero.')

    cp = getParameterValue(7)
    If (cp<=0.) Call FoundBadParameter(7,'Fatal','The specific heat of the tank fluid must be greater than zero.')

    rho = getParameterValue(8)
    If (rho<=0.) Call FoundBadParameter(8,'Fatal','The density of the tank fluid must be greater than zero.')

    thermal_cond = getParameterValue(9)
    If (thermal_cond<=0.) Call FoundBadParameter(9,'Fatal','The thermal conductivity of the tank fluid must be greater than zero.')

    f_inlet_1 = getParameterValue(10)
    If (f_inlet_1<0.) Call FoundBadParameter(10,'Fatal','The normalized height of the first inlet to the tank must be between 0 (the bottom) and 1 (the top).')
    If (f_inlet_1>1.) Call FoundBadParameter(10,'Fatal','The normalized height of the first inlet to the tank must be between 0 (the bottom) and 1 (the top).')

    f_outlet_1 = getParameterValue(11)
    If (f_outlet_1<0.) Call FoundBadParameter(11,'Fatal','The normalized height of the first outlet from the tank must be between 0 (the bottom) and 1 (the top).')
    If (f_outlet_1>1.) Call FoundBadParameter(11,'Fatal','The normalized height of the first outlet from the tank must be between 0 (the bottom) and 1 (the top).')

    f_inlet_2 = getParameterValue(12)
    If (f_inlet_2<0.) Call FoundBadParameter(12,'Fatal','The normalized height of the second inlet to the tank must be between 0 (the bottom) and 1 (the top).')
    If (f_inlet_2>1.) Call FoundBadParameter(12,'Fatal','The normalized height of the second inlet to the tank must be between 0 (the bottom) and 1 (the top).')

    f_outlet_2 = getParameterValue(13)
    If (f_outlet_2<0.) Call FoundBadParameter(13,'Fatal','The normalized height of the second outlet from the tank must be between 0 (the bottom) and 1 (the top).')
    If (f_outlet_2>1.) Call FoundBadParameter(13,'Fatal','The normalized height of the second outlet from the tank must be between 0 (the bottom) and 1 (the top).')

    N_THERMOSTATS=JFIX(getParameterValue(14)+0.1)
    If (N_THERMOSTATS>N_THERMOSTATS_MAX) Call FoundBadParameter(14,'Fatal','The number of thermostats supplied is greater than that currently allowed by the source code.')
    If (ErrorFound()) Return
    
    Do j=1,N_THERMOSTATS
       f_thermostat(j)=getParameterValue(14+j)
       If (f_thermostat(j)<0.) Call FoundBadParameter(14+j,'Fatal','The normalized height of the specified thermostat in the tank must be between 0 (the bottom) and 1 (the top).')
       If (f_thermostat(j)>1.) Call FoundBadParameter(14+j,'Fatal','The normalized height of the specified thermostat in the tank must be between 0 (the bottom) and 1 (the top).')
    EndDo

    N_HEATERS=JFIX(getParameterValue(15+N_THERMOSTATS)+0.1)
    If (N_HEATERS>N_HEATERS_MAX) Call FoundBadParameter(15+N_THERMOSTATS,'Fatal','The number of auxiliary heat inputs supplied is greater than that currently allowed by the source code.')
    If (ErrorFound()) Return
    
    Do j=1,N_HEATERS
       f_heater(j)=getParameterValue(15+N_THERMOSTATS+j)
       If (f_heater(j)<0.) Call FoundBadParameter(15+N_THERMOSTATS+j,'Fatal','The normalized height of the specified auxiliary heat input into the tank must be between 0 (the bottom) and 1 (the top).')
       If (f_heater(j)>1.) Call FoundBadParameter(15+N_THERMOSTATS+j,'Fatal','The normalized height of the specified auxiliary heat input into the tank must be between 0 (the bottom) and 1 (the top).')
    EndDo
    If (ErrorFound()) Return
    
   !Get the initial tank temperatures
    temp_avg_tank=0.
    Do j=1,N_NODES
       nodes_tank_temp_initial(j)=getNumericalSolution(j)
       temp_avg_tank=temp_avg_tank+nodes_tank_temp_initial(j)/DBLE(N_NODES)
    EndDo

   !Set the Initial Values of the Outputs
    Call setOutputValue(1,temp_avg_tank)
    Call setOutputValue(2,0.d0)
    Call setOutputValue(3,temp_avg_tank)
    Call setOutputValue(4,0.d0)
    Call setOutputValue(5,temp_avg_tank)
    Call setOutputValue(6,0.d0)
    Call setOutputValue(7,0.d0)
    Call setOutputValue(8,0.d0)
    Call setOutputValue(9,0.d0)
    Call setOutputValue(10,0.d0)
    Call setOutputValue(11,0.d0)
    Call setOutputValue(12,0.d0)
    Call setOutputValue(13,0.d0)

    Do j=1,N_THERMOSTATS
       Call setOutputValue(13+j,temp_avg_tank)
    EndDo

    Do j=1,N_NODES
       Call setOutputValue(13+N_THERMOSTATS+j,nodes_tank_temp_initial(j))
    EndDo

   !Set the Initial Values of the Dynamic Storage Variables
    Do j=1,N_NODES
       Call SetDynamicArrayInitialValue(j,nodes_tank_temp_initial(j))
    EndDo

    !Initialize SSR variables
    If (getIsIncludedInSSR()) Then
       Call initReportIntegral(1,'Delivered Energy from Port 1','kJ/h','kJ')
       Call initReportIntegral(2,'Delivered Energy from Port 2','kJ/h','kJ')
       Call initReportIntegral(3,'Auxiliary Energy','kJ/h','kJ')
       Call initReportIntegral(4,'Thermal Losses','kJ/h','kJ')
       Call initReportMinMax(1,'Outlet Temperature Port 1','C')
       Call initReportMinMax(2,'Outlet Temperature Port 2','C')
       Call initReportMinMax(3,'Average Tank Temperature','C')
       Call initReportValue(1,'Tank Volume',vol,'m3')
       Call initReportValue(2,'# of Tank Nodes',dble(N_NODES),'-')
       Call initReportValue(3,'# of Thermostats',dble(N_THERMOSTATS),'-')
       Call initReportValue(4,'# of Auxiliary Inputs',dble(N_HEATERS),'-')
    EndIf  

   Return

 EndIf
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!ReRead the Parameters if Another Unit of This Type Has Been Called Last
 If(getIsReReadParameters()) Then
    vol = getParameterValue(1)
    height = getParameterValue(2)
    N_NODES=JFIX(getParameterValue(3)+0.1)
    U_top = getParameterValue(4)
    U_edge = getParameterValue(5)
    U_bottom = getParameterValue(6)
    cp = getParameterValue(7)
    rho = getParameterValue(8)
    thermal_cond = getParameterValue(9)
    f_inlet_1 = getParameterValue(10)
    f_outlet_1 = getParameterValue(11)
    f_inlet_2 = getParameterValue(12)
    f_outlet_2 = getParameterValue(13)
    N_THERMOSTATS=JFIX(getParameterValue(14)+0.1)
    Do j=1,N_THERMOSTATS
       f_thermostat(j)=getParameterValue(14+j)
    EndDo
    N_HEATERS=JFIX(getParameterValue(15+N_THERMOSTATS)+0.1)
    Do j=1,N_HEATERS
       f_heater(j)=getParameterValue(15+N_THERMOSTATS+j)
    EndDo
 EndIf
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Get the Input Values
 ports_temp_in(1)=getInputValue(1)
 ports_massflow_in(1)=getInputValue(2)
 ports_temp_in(2)=getInputValue(3)
 ports_massflow_in(2)=getInputValue(4)
 temp_top_loss=getInputValue(5)
 temp_edge_loss=getInputValue(6)
 temp_bottom_loss=getInputValue(7)
 
 Do j=1,N_HEATERS
    heaters_Q_input(j)=getInputValue(7+j)
 EndDo
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Check the Inputs for Problems (#,ErrorType,Text)
 If(ports_massflow_in(1) < 0.) Call FoundBadInput(2,'Fatal','The flow rate through the tank must be greater than or equal to zero.')
 If(ports_massflow_in(2) < 0.) Call FoundBadInput(4,'Fatal','The flow rate through the tank must be greater than or equal to zero.')
 If(ErrorFound()) Return
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Calculate parameter dependent values

!Get the nodes for the port inlets and outlets
 nodes_ports_inlet(1)=0
 nodes_ports_inlet(2)=0
 nodes_ports_outlet(1)=0
 nodes_ports_outlet(2)=0
 
 Do j=N_NODES,1,-1
    f_now=DBLE(N_NODES-j+1)/DBLE(N_NODES)
    If((f_inlet_1<f_now).and.(nodes_ports_inlet(1)==0)) nodes_ports_inlet(1)=j
    If((f_inlet_2<f_now).and.(nodes_ports_inlet(2)==0)) nodes_ports_inlet(2)=j
    If((f_outlet_1<f_now).and.(nodes_ports_outlet(1)==0)) nodes_ports_outlet(1)=j
    If((f_outlet_2<f_now).and.(nodes_ports_outlet(2)==0)) nodes_ports_outlet(2)=j
 EndDo
 If(f_inlet_1>=1.) nodes_ports_inlet(1)=1
 If(f_inlet_2>=1.) nodes_ports_inlet(2)=1
 If(f_outlet_1>=1.) nodes_ports_outlet(1)=1
 If(f_outlet_2>=1.) nodes_ports_outlet(2)=1

!Set the fraction of the inlet flow to 1 for the inlet node and to 0 otherwise
 Do j=1,N_NODES
    If(j==nodes_ports_inlet(1)) Then
       ports_f_inlet(1,j)=1.
    Else
       ports_f_inlet(1,j)=0.
    EndIf
    
    If(j==nodes_ports_inlet(2)) Then
       ports_f_inlet(2,j)=1.
    Else
       ports_f_inlet(2,j)=0.
    EndIf
 EndDo

!Calculate the node containing the thermostats
 Do k=1,N_THERMOSTATS
    nodes_thermostat(k)=0
    Do j=N_NODES,1,-1
       f_now=DBLE(N_NODES-j+1)/DBLE(N_NODES)
       If((f_thermostat(k)<f_now).and.(nodes_thermostat(k)==0)) nodes_thermostat(k)=j
    EndDo
    If(f_thermostat(k)>=1.) nodes_thermostat(k)=1
 EndDo

!Calculate the node containing the auxiliary heat input
 Do k=1,N_HEATERS
    nodes_heaters(k)=0
    Do j=N_NODES,1,-1
       f_now=DBLE(N_NODES-j+1)/DBLE(N_NODES)
       If((f_heater(k)<f_now).and.(nodes_heaters(k)==0)) nodes_heaters(k)=j
    EndDo
    If(f_heater(k)>=1.) nodes_heaters(k)=1
 EndDo

!Calculate the volume of each tank node
 Do j=1,N_NODES
    nodes_vol(j)=vol/DBLE(N_NODES)
 EndDo

!Calculate the radius of the tank
 tank_radius=(vol/Pi/height)**0.5

!Set the capacitance of each tank node
 Do j=1,N_NODES
    nodes_capacitance(j)=nodes_vol(j)*rho*cp
 EndDo

!Calculate the surface areas for the single node case
 If(N_NODES==1) Then
    area_top_surface(1)=Pi*tank_radius*tank_radius
    area_bottom_surface(1)=Pi*tank_radius*tank_radius
    area_edges(1)=2.*Pi*tank_radius*height
    area_conduction(1)=Pi*tank_radius*tank_radius
    length_conduction(1)=height/2.
    
!Calculate the surface areas for the multiple node case
 Else
    Do j=1,N_NODES
       If(j==1) Then
          area_top_surface(j)=Pi*tank_radius*tank_radius
          area_bottom_surface(j)=0.
          area_edges(j)=2.*Pi*tank_radius*height/DBLE(N_NODES)
          area_conduction(j)=Pi*tank_radius*tank_radius
          length_conduction(j)=height/DBLE(N_NODES)
       Else If(j==N_NODES) Then
          area_top_surface(j)=0.
          area_bottom_surface(j)=Pi*tank_radius*tank_radius
          area_edges(j)=2.*Pi*tank_radius*height/DBLE(N_NODES)
          area_conduction(j)=Pi*tank_radius*tank_radius
          length_conduction(j)=height/DBLE(N_NODES)
       Else
          area_top_surface(j)=0.
          area_bottom_surface(j)=0.
          area_edges(j)=2.*Pi*tank_radius*height/DBLE(N_NODES)
          area_conduction(j)=Pi*tank_radius*tank_radius
          length_conduction(j)=height/DBLE(N_NODES)
       EndIf
    EndDo
 EndIf


!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Get the Initial Values of the Dynamic Variables from the Global Storage Array
 Do j=1,N_NODES
    nodes_tank_temp_initial(j)=getDynamicArrayValueLastSTEP_s(j)
    nodes_tank_temp_start(j)=getDynamicArrayValueLastSTEP_s(j)
    nodes_tank_temp_final(j)=getDynamicArrayValueLastSTEP_s(j)
    nodes_tank_temp_avg(j)=getDynamicArrayValueLastSTEP_s(j)
 EndDo
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Main calculation loop
 ITER_MAX=20
 
!Indicate that the temperatures have not been checked for stability
 Do j=1,N_NODES
    stability_checked(j)=.False.
    iterations_tank(j)=1
 EndDo

!Set some initial conditions for the iterative calculations
 iterations_tank_max=1
 checking_temperatures=.True.
 heat_edge_loss=0.
 heat_bottom_loss=0.
 heat_top_loss=0.
 heat_heaters_total=0.
 heat_stored_tank=0.
 heat_delivered_port=0.
 heat_delivered_total=0.

!Start the iterative calculations here - everything above this point is independent of the iterative scheme
 200 Continue

!Reset the differential equation terms AA and BB where  dT/dt=AA*T+BB
 Do j=1,N_NODES
    AA(j)=0.
    BB(j)=0.
 EndDo

!Set the flow rate for each node from each port
 N_PORTS=2
 
 Do i=1,N_PORTS
    Do j=1,N_NODES
       massflow_mains(i,j)=ports_massflow_in(i)*ports_f_inlet(i,j)
    EndDo
 EndDo

!Set the inlet temperatures and flows to each tank node from each port
 Do i=1,N_PORTS

   !Start at the bottom and works towards the outlet
    Do j=N_NODES,1,-1
       If(j==nodes_ports_outlet(i)) EXIT
     
       If(j==N_NODES) Then
          temp_load_in(i,j)=nodes_tank_temp_avg(j)
          massflow_load_in(i,j)=0.
          massflow_load_out(i,j)=massflow_mains(i,j)
       Else
          temp_load_in(i,j)=nodes_tank_temp_avg(j+1)
          massflow_load_in(i,j)=massflow_load_out(i,j+1)
          massflow_load_out(i,j)=massflow_mains(i,j)+massflow_load_in(i,j)
       EndIf
    EndDo
          
   !Now start at the top and works towards the outlet
    Do j=1,N_NODES
       If(j==nodes_ports_outlet(i)) EXIT
     
       If(j==1) Then
          temp_load_in(i,j)=nodes_tank_temp_avg(j)
          massflow_load_in(i,j)=0.
          massflow_load_out(i,j)=massflow_mains(i,j)
       Else
          temp_load_in(i,j)=nodes_tank_temp_avg(j-1)
          massflow_load_in(i,j)=massflow_load_out(i,j-1)
          massflow_load_out(i,j)=massflow_mains(i,j)+massflow_load_in(i,j)
       EndIf
    EndDo
 EndDo

!Handle the single node tank case
 If(N_NODES==1) Then
    Do i=1,N_PORTS
       massflow_load_in(i,1)=0.
       massflow_load_out(i,1)=massflow_mains(i,1)
    EndDo
 EndIf

!Set the AA and BB terms for the nodal differential equation for the inlet flows
 Do i=1,N_Ports
    Do j=1,N_NODES
       If(N_NODES==1) Then
          AA(j)=AA(j)-massflow_mains(i,j)*cp/nodes_capacitance(j)
          BB(j)=BB(j)+massflow_mains(i,j)*cp*ports_temp_in(i)/nodes_capacitance(j)
       Else If(j.NE.nodes_ports_outlet(i)) Then
          AA(j)=AA(j)-massflow_load_out(i,j)*cp/nodes_capacitance(j)
          BB(j)=BB(j)+(massflow_mains(i,j)*cp*ports_temp_in(i)+massflow_load_in(i,j)*cp*temp_load_in(i,j))/nodes_capacitance(j)
       Else
          If(j==1) Then
             massflow_load_out(i,j)=ports_massflow_in(i)
             massflow_load_in(i,j)=massflow_load_out(i,j+1)
             
             temp_load_in(i,j)=nodes_tank_temp_avg(j+1)

             AA(j)=AA(j)-massflow_load_out(i,j)*cp/nodes_capacitance(j)
             BB(j)=BB(j)+(massflow_mains(i,j)*cp*ports_temp_in(i)+massflow_load_in(i,j)*cp*temp_load_in(i,j))/nodes_capacitance(j)
          
          Else If(j==N_NODES) Then
             massflow_load_out(i,j)=ports_massflow_in(i)
             massflow_load_in(i,j)=massflow_load_out(i,j-1)
             
             temp_load_in(i,j)=nodes_tank_temp_avg(j-1)

             AA(j)=AA(j)-massflow_load_out(i,j)*cp/nodes_capacitance(j)
             BB(j)=BB(j)+(massflow_mains(i,j)*cp*ports_temp_in(i)+massflow_load_in(i,j)*cp*temp_load_in(i,j))/nodes_capacitance(j)
          
          Else
             massflow_load_out(i,j)=ports_massflow_in(i)
             massflow_load_in(i,j)=massflow_load_out(i,j-1)+massflow_load_out(i,j+1)
             
             If((ports_massflow_in(i)>0.).AND.((massflow_load_out(i,j-1)+massflow_load_out(i,j+1))>0.)) Then
                temp_load_in(i,j)=(nodes_tank_temp_avg(j-1)*massflow_load_out(i,j-1)+nodes_tank_temp_avg(j+1)*massflow_load_out(i,j+1))/(massflow_load_out(i,j-1)+massflow_load_out(i,j+1))
             Else
                temp_load_in(i,j)=nodes_tank_temp_avg(j)
             EndIf

             AA(j)=AA(j)-massflow_load_out(i,j)*cp/nodes_capacitance(j)
             BB(j)=BB(j)+(massflow_mains(i,j)*cp*ports_temp_in(i)+massflow_load_out(i,j-1)*cp*nodes_tank_temp_avg(j-1)+massflow_load_out(i,j+1)*cp*nodes_tank_temp_avg(j+1))/nodes_capacitance(j)
          EndIf
       EndIf
    EndDo
 EndDo

!Set the AA and BB terms for the nodal differential equation for the auxiliary heaters
 Do k=1,N_HEATERS
    BB(nodes_heaters(k))=BB(nodes_heaters(k))+heaters_Q_input(k)/nodes_capacitance(nodes_heaters(k))
 EndDo

!Set the AA and BB terms for the nodal differential equation for the thermal losses from the top surface
 Do j=1,N_NODES
    UA_top_surface=U_top*area_top_surface(j)
    AA(j)=AA(j)-UA_top_surface/nodes_capacitance(j)
    BB(j)=BB(j)+UA_top_surface*temp_top_loss/nodes_capacitance(j)
 EndDo

!Set the AA and BB terms for the nodal differential equation for the thermal losses from the edge surfaces
 Do j=1,N_NODES
    UA_edges=U_edge*area_edges(j)
    AA(j)=AA(j)-UA_edges/nodes_capacitance(j)
    BB(j)=BB(j)+UA_edges*temp_edge_loss/nodes_capacitance(j)
 EndDo

!Set the AA and BB terms for the nodal differential equation for the thermal losses from the bottom surface
 Do j=1,N_NODES
    UA_bottom_surface=U_bottom*area_bottom_surface(j)
    AA(j)=AA(j)-UA_bottom_surface/nodes_capacitance(j)
    BB(j)=BB(j)+UA_bottom_surface*temp_bottom_loss/nodes_capacitance(j)
 EndDo

!Set the AA and BB terms for the nodal differential equation for conduction between nodes
 If (N_NODES > 1) Then
     Do j=1,N_NODES
        If(j==1) Then
           AA(j)=AA(j)-thermal_cond*area_conduction(j)/length_conduction(j)/nodes_capacitance(j)
           BB(j)=BB(j)+thermal_cond*area_conduction(j)/length_conduction(j)*nodes_tank_temp_avg(j+1)/nodes_capacitance(j)
        Else If(j==N_NODES) Then
           AA(j)=AA(j)-thermal_cond*area_conduction(j-1)/length_conduction(j-1)/nodes_capacitance(j)
           BB(j)=BB(j)+thermal_cond*area_conduction(j-1)/length_conduction(j-1)*nodes_tank_temp_avg(j-1)/nodes_capacitance(j)
        Else
           AA(j)=AA(j)-thermal_cond*area_conduction(j)/length_conduction(j)/nodes_capacitance(j)-thermal_cond*area_conduction(j-1)/length_conduction(j-1)/nodes_capacitance(j)
           BB(j)=BB(j)+thermal_cond*area_conduction(j)/length_conduction(j)*nodes_tank_temp_avg(j+1)/nodes_capacitance(j)+thermal_cond*area_conduction(j-1)/length_conduction(j-1)*nodes_tank_temp_avg(j-1)/nodes_capacitance(j)
        EndIf
     EndDo
 EndIf

!Determine the final and average tank node temperatures
 Do j=1,N_NODES
    If(AA(j)==0.) Then
       nodes_tank_temp_final_New(j)=nodes_tank_temp_initial(j)+BB(j)*STEP_s
       nodes_tank_temp_avg_New(j)=nodes_tank_temp_initial(j)+BB(j)*STEP_s/2.
    Else
       nodes_tank_temp_final_New(j)=(nodes_tank_temp_initial(j)+BB(j)/AA(j))*DEXP(AA(j)*STEP_s)-BB(j)/AA(j)
       nodes_tank_temp_avg_New(j)=(nodes_tank_temp_initial(j)+BB(j)/AA(j))*(DEXP(AA(j)*STEP_s)-1.)/AA(j)/STEP_s-BB(j)/AA(j)
    EndIf
 EndDo

!See If the tank node temperatures have converged
 converged_tank=.TRUE.
 Do j=1,N_NODES
    If((DABS(nodes_tank_temp_avg_New(j)-nodes_tank_temp_avg(j))>conv_criteria).AND.(iterations_tank(j)<=ITER_MAX)) Then
       converged_tank=.FALSE.
       iterations_tank(j)=iterations_tank(j)+1
       iterations_tank_max=MAX(iterations_tank_max,iterations_tank(j))
    EndIf
 EndDo
          
 If(converged_tank) Then
    If(iterations_tank_max>=ITER_MAX) Then
       iteration_limit_reached_tank=.TRUE.
    Else
       iteration_limit_reached_tank=.FALSE.
    EndIf

    Do j=1,N_NODES
       nodes_tank_temp_avg(j)=nodes_tank_temp_avg_New(j)
       nodes_tank_temp_final(j)=nodes_tank_temp_final_New(j)
    EndDo
 Else
    Do j=1,N_NODES
       nodes_tank_temp_avg(j)=nodes_tank_temp_avg_New(j)
       nodes_tank_temp_final(j)=nodes_tank_temp_final_New(j)
    EndDo
         
    GoTo 200
 EndIf
 
!Calculate the average temperatures
 temp_avg_tank=0.
 Do j=1,N_NODES
    temp_avg_tank=temp_avg_tank+nodes_tank_temp_avg(j)/DBLE(N_NODES)
 EndDo

!Calculate the tank energy flows
 Do j=1,N_NODES
    UA_edges=U_edge*area_edges(j)
    heat_edge_loss=heat_edge_loss+UA_edges*(nodes_tank_temp_avg(j)-temp_edge_loss)
    UA_bottom_surface=U_bottom*area_bottom_surface(j)
    heat_bottom_loss=heat_bottom_loss+UA_bottom_surface*(nodes_tank_temp_avg(j)-temp_bottom_loss)
    UA_top_surface=U_top*area_top_surface(j)
    heat_top_loss=heat_top_loss+UA_top_surface*(nodes_tank_temp_avg(j)-temp_top_loss)
    heat_stored_tank=heat_stored_tank+nodes_capacitance(j)*(nodes_tank_temp_final(j)-nodes_tank_temp_start(j))/TimeStep
         
    Do i=1,N_Ports
       heat_delivered_port(i)=heat_delivered_port(i)+massflow_load_out(i,j)*cp*nodes_tank_temp_avg(j)-massflow_mains(i,j)*cp*ports_temp_in(i)-massflow_load_in(i,j)*cp*temp_load_in(i,j)
    EndDo
 EndDo
    
 Do i=1,N_HEATERS
    heat_heaters_total=heat_heaters_total+heaters_Q_input(i)
 EndDo

 Do i=1,N_Ports
    heat_delivered_total=heat_delivered_total+heat_delivered_port(i)
 EndDo

!Calculate the energy balance errors
 energy_balance_numerator_tank=heat_stored_tank+heat_edge_loss+heat_bottom_loss+heat_top_loss+heat_delivered_total-heat_heaters_total
 energy_balance_denominator_tank=DABS(heat_top_loss)+DABS(heat_delivered_total)+DABS(heat_edge_loss)+DABS(heat_bottom_loss)+DABS(heat_heaters_total)
 energy_balance_error_tank=DABS(energy_balance_numerator_tank)/DMAX1(1.0,energy_balance_denominator_tank)*100.
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Perform an instantaneous adiabatic mixing to eliminate temperature inversions
 5150 Continue

 Do j=1,N_NODES-1
    If(nodes_tank_temp_final(j)<nodes_tank_temp_final(j+1)) Goto 5165
 EndDo

!Update the dynamic variables
 Do j=1,N_NODES
    Call SetDynamicArrayValueThisIteration(j,nodes_tank_temp_final(j))
 EndDo

 Goto 300

 5165 Continue

 temp_mixed = 0.
 capacitance_mixed = 0.
 Do m=j,N_NODES
    temp_mixed = temp_mixed + nodes_tank_temp_final(m)*nodes_capacitance(m)
    capacitance_mixed = capacitance_mixed + nodes_capacitance(m)
    If(m==N_NODES) Goto 5185
    If(temp_mixed/capacitance_mixed>nodes_tank_temp_final(m+1)) Goto 5185
 EndDo

 5185 Continue
 
 temp_mixed = temp_mixed/capacitance_mixed
      
 Do k=j,m
    If(AA(k)==0.) Then
       mixing_final_factor = TimeStep/nodes_capacitance(k)
       mixing_avg_factor = mixing_final_factor/2.
    Else
       mixing_final_factor=(DEXP(AA(k)*TimeStep)-1.)/AA(k)/nodes_capacitance(k)
       mixing_avg_factor=((DEXP(AA(k)*TimeStep)-1.)/AA(k)/TimeStep-1.)/AA(k)/nodes_capacitance(k)
    EndIf
         
    mixing_q_adiabatic=(temp_mixed-nodes_tank_temp_final(k))/mixing_final_factor
         
    nodes_tank_temp_final(k)=temp_mixed
    nodes_tank_temp_avg(k)=nodes_tank_temp_avg(k)+mixing_q_adiabatic*mixing_avg_factor
 EndDo
    
 Goto 5150
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Set the Outputs from this Model (#,Value)
300 Continue
    
 Call setOutputValue(1,nodes_tank_temp_avg(nodes_ports_outlet(1)))
 Call setOutputValue(2,ports_massflow_in(1))
 Call setOutputValue(3,nodes_tank_temp_avg(nodes_ports_outlet(2)))
 Call setOutputValue(4,ports_massflow_in(2))
 Call setOutputValue(5,temp_avg_tank)
 Call setOutputValue(6,heat_delivered_port(1))
 Call setOutputValue(7,heat_delivered_port(2))
 Call setOutputValue(8,heat_top_loss)
 Call setOutputValue(9,heat_edge_loss)
 Call setOutputValue(10,heat_bottom_loss)
 Call setOutputValue(11,heat_heaters_total)
 Call setOutputValue(12,heat_stored_tank)
 Call setOutputValue(13,energy_balance_error_tank)

 Do j=1,N_THERMOSTATS
    Call setOutputValue(13+j,nodes_tank_temp_avg(nodes_thermostat(j)))
 EndDo

 Do j=1,N_NODES
    Call setOutputValue(13+N_THERMOSTATS+j,nodes_tank_temp_avg(j))
 EndDo
!-----------------------------------------------------------------------------------------------------------------------

 Return
 End
