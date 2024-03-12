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
 Integer N_Nodes_Max,N_Thermostats_Max,N_AuxLocations_Max
 Parameter (N_Nodes_Max=50,N_Thermostats_Max=5,N_AuxLocations_Max=5)
 Integer i,j,k,m,N_Nodes,N_Thermostats,N_AuxLocations,Node_Outlet(2),Node_Thermostat(N_Thermostats_Max),Node_Inlet(2), &
    Node_Auxiliary(N_AuxLocations_Max),Iterations_Max,Iterations_Tank_Max,N_Ports,Iterations_Tank(N_Nodes_Max)
 Double Precision Time,Timestep,StartTime,StopTime,Pi,ConvergenceCriteria,Volume_Tank,Height_Tank,U_Top,U_Edge,U_Bottom, &
    SpecificHeat_TankFluid,Density_TankFluid,Conductivity_TankFluid,FracHeight_Inlet1,FracHeight_Outlet1,FracHeight_Inlet2, &
    FracHeight_Outlet2,FracHeight_Tstat(N_Thermostats_Max),FracHeight_Aux(N_AuxLocations_Max),Averagefactor_Mixing, &
    Q_AdiabaticMixing,Tinitial_TankNode(N_Nodes_Max),Taverage_TankNode(N_Nodes_Max),Tfinal_TankNode(N_Nodes_Max), &
    Mdot_Flow_in(2),Q_Delivered_Total,Taverage_Tank,Q_Delivered_Port(2),Q_TopLoss,Q_EdgeLoss,Q_BottomLoss,Q_Auxiliary_Total, &
    Q_Stored_Tank,EnergyBalance_Error_Tank,T_Flow_in(2),T_TopLoss,T_EdgeLoss,T_BottomLoss,Q_AuxiliaryInput(N_AuxLocations_Max), &
    Fraction_Inlet(2,N_Nodes_Max),Frac_Now,Volume_TankNode(N_Nodes_Max),Radius_Tank,Area_TopSurface(N_Nodes_Max), &
    Area_BottomSurface(N_Nodes_Max),Area_Edges(N_Nodes_Max),ConductionArea(N_Nodes_Max),L_Conduction(N_Nodes_Max), &
    Capacitance_TankNode(N_Nodes_Max),Tstart_TankNode(N_Nodes_Max),AA(N_Nodes_Max),BB(N_Nodes_Max),Mdot_Mains(2,N_Nodes_Max), &
    T_Load_In(2,N_Nodes_Max),Mdot_Load_In(2,N_Nodes_Max),Mdot_Load_Out(2,N_Nodes_Max),UA_TopSurface,UA_Edges,UA_BottomSurface, &
    Tfinal_TankNode_New(N_Nodes_Max),Taverage_TankNode_New(N_Nodes_Max),EnergyBalance_Numerator_Tank,EnergyBalance_Denominator_Tank, &
    T_Mixed,Capacitance_Mixed,Finalfactor_Mixing
 Logical StabilityChecked(N_Nodes_Max),CheckingTemperatures,Converged_Tank,IterationLimitReached_Tank
 Data Pi/3.14159265358979/,ConvergenceCriteria/0.0001/
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
!Perform Any "After Convergence" Manipulations That May Be Required at the End of Each Timestep
 If(getIsEndofTimestep()) Then
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
    N_Nodes=JFIX(getParameterValue(3)+0.1)
    N_Thermostats=JFIX(getParameterValue(14)+0.1)
    N_AuxLocations=JFIX(getParameterValue(15+N_Thermostats)+0.1)

    If (N_Nodes<=0) Call FoundBadParameter(3,'Fatal','The number of isothermal tank nodes must be greater than zero.')
    If (N_Nodes>N_Nodes_Max) Call FoundBadParameter(3,'Fatal','The number of isothermal tank nodes supplied is greater than that currently allowed by the source code.')
    If (N_Thermostats<0) Call FoundBadParameter(14,'Fatal','The number of thermostats must be greater than or equal to zero.')
    If (N_AuxLocations<0) Call FoundBadParameter(15+N_Thermostats,'Fatal','The number of auxiliary heat inputs must be greater than or equal to zero.')
    If (ErrorFound()) Return

    Call SetNumberofParameters(15+N_Thermostats+N_AuxLocations) 
    Call SetNumberofInputs(7+N_AuxLocations) 
    Call SetNumberofDerivatives(N_Nodes) 
    Call SetNumberofOutputs(13+N_Thermostats+N_Nodes) 
    Call SetIterationMode(1) 
    Call SetNumberStoredVariables(0,N_Nodes) 
    Call SetNumberofDiscreteControls(0) 

!  Set the Correct Input and Output Variable Types
    Call SetInputUnits(1,'TE1')
    Call SetInputUnits(2,'MF1')
    Call SetInputUnits(3,'TE1')
    Call SetInputUnits(4,'MF1')
    Call SetInputUnits(5,'TE1')
    Call SetInputUnits(6,'TE1')
    Call SetInputUnits(7,'TE1')
    
    Do j=1,N_AuxLocations
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
    
    Do j=1,N_Thermostats
       Call SetOutputUnits(13+j,'TE1')
    EndDo

    Do j=1,N_Nodes
       Call SetOutputUnits(13+N_Thermostats+j,'TE1')
    EndDo

    ! Set up this Type's entry in the SSR
    If (getIsIncludedInSSR()) Then
       Call setNumberOfReportVariables(4,3,4,0) !(nInt,nMinMax,nVals,nText)
    EndIf 

    Return

 EndIf
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Do All of the First Timestep Manipulations Here - There Are No Iterations at the Intial Time
 If (getIsStartTime()) Then
      
   !Read in the Values of the Parameters from the Input File and Check for Problems
    Volume_Tank = getParameterValue(1)
    If (Volume_Tank<=0.) Call FoundBadParameter(1,'Fatal','The tank volume must be greater than zero.')

    Height_Tank = getParameterValue(2)
    If (Height_Tank<=0.) Call FoundBadParameter(2,'Fatal','The height of the tank must be greater than zero.')

    N_Nodes=JFIX(getParameterValue(3)+0.1)
    If (N_Nodes<=0) Call FoundBadParameter(3,'Fatal','The number of isothermal tank nodes must be greater than zero.')

    U_Top = getParameterValue(4)
    If (U_Top<0.) Call FoundBadParameter(4,'Fatal','The heat loss coefficient for the tank top surface must be greater than or equal to zero.')

    U_Edge = getParameterValue(5)
    If (U_Edge<0.) Call FoundBadParameter(5,'Fatal','The heat loss coefficient for the tank edges must be greater than or equal to zero.')

    U_Bottom = getParameterValue(6)
    If (U_Bottom<0.) Call FoundBadParameter(6,'Fatal','The heat loss coefficient for the tank bottom surface must be greater than or equal to zero.')

    SpecificHeat_TankFluid = getParameterValue(7)
    If (SpecificHeat_TankFluid<=0.) Call FoundBadParameter(7,'Fatal','The specific heat of the tank fluid must be greater than zero.')

    Density_TankFluid = getParameterValue(8)
    If (Density_TankFluid<=0.) Call FoundBadParameter(8,'Fatal','The density of the tank fluid must be greater than zero.')

    Conductivity_TankFluid = getParameterValue(9)
    If (Conductivity_TankFluid<=0.) Call FoundBadParameter(9,'Fatal','The thermal conductivity of the tank fluid must be greater than zero.')

    FracHeight_Inlet1 = getParameterValue(10)
    If (FracHeight_Inlet1<0.) Call FoundBadParameter(10,'Fatal','The normalized height of the first inlet to the tank must be between 0 (the bottom) and 1 (the top).')
    If (FracHeight_Inlet1>1.) Call FoundBadParameter(10,'Fatal','The normalized height of the first inlet to the tank must be between 0 (the bottom) and 1 (the top).')

    FracHeight_Outlet1 = getParameterValue(11)
    If (FracHeight_Outlet1<0.) Call FoundBadParameter(11,'Fatal','The normalized height of the first outlet from the tank must be between 0 (the bottom) and 1 (the top).')
    If (FracHeight_Outlet1>1.) Call FoundBadParameter(11,'Fatal','The normalized height of the first outlet from the tank must be between 0 (the bottom) and 1 (the top).')

    FracHeight_Inlet2 = getParameterValue(12)
    If (FracHeight_Inlet2<0.) Call FoundBadParameter(12,'Fatal','The normalized height of the second inlet to the tank must be between 0 (the bottom) and 1 (the top).')
    If (FracHeight_Inlet2>1.) Call FoundBadParameter(12,'Fatal','The normalized height of the second inlet to the tank must be between 0 (the bottom) and 1 (the top).')

    FracHeight_Outlet2 = getParameterValue(13)
    If (FracHeight_Outlet2<0.) Call FoundBadParameter(13,'Fatal','The normalized height of the second outlet from the tank must be between 0 (the bottom) and 1 (the top).')
    If (FracHeight_Outlet2>1.) Call FoundBadParameter(13,'Fatal','The normalized height of the second outlet from the tank must be between 0 (the bottom) and 1 (the top).')

    N_Thermostats=JFIX(getParameterValue(14)+0.1)
    If (N_Thermostats>N_Thermostats_Max) Call FoundBadParameter(14,'Fatal','The number of thermostats supplied is greater than that currently allowed by the source code.')
    If (ErrorFound()) Return
    
    Do j=1,N_Thermostats
       FracHeight_Tstat(j)=getParameterValue(14+j)
       If (FracHeight_Tstat(j)<0.) Call FoundBadParameter(14+j,'Fatal','The normalized height of the specified thermostat in the tank must be between 0 (the bottom) and 1 (the top).')
       If (FracHeight_Tstat(j)>1.) Call FoundBadParameter(14+j,'Fatal','The normalized height of the specified thermostat in the tank must be between 0 (the bottom) and 1 (the top).')
    EndDo

    N_AuxLocations=JFIX(getParameterValue(15+N_Thermostats)+0.1)
    If (N_AuxLocations>N_AuxLocations_Max) Call FoundBadParameter(15+N_Thermostats,'Fatal','The number of auxiliary heat inputs supplied is greater than that currently allowed by the source code.')
    If (ErrorFound()) Return
    
    Do j=1,N_AuxLocations
       FracHeight_Aux(j)=getParameterValue(15+N_Thermostats+j)
       If (FracHeight_Aux(j)<0.) Call FoundBadParameter(15+N_Thermostats+j,'Fatal','The normalized height of the specified auxiliary heat input into the tank must be between 0 (the bottom) and 1 (the top).')
       If (FracHeight_Aux(j)>1.) Call FoundBadParameter(15+N_Thermostats+j,'Fatal','The normalized height of the specified auxiliary heat input into the tank must be between 0 (the bottom) and 1 (the top).')
    EndDo
    If (ErrorFound()) Return
    
   !Get the initial tank temperatures
    Taverage_Tank=0.
    Do j=1,N_Nodes
       Tinitial_TankNode(j)=getNumericalSolution(j)
       Taverage_Tank=Taverage_Tank+Tinitial_TankNode(j)/DBLE(N_Nodes)
    EndDo

   !Set the Initial Values of the Outputs
    Call setOutputValue(1,Taverage_Tank)
    Call setOutputValue(2,0.d0)
    Call setOutputValue(3,Taverage_Tank)
    Call setOutputValue(4,0.d0)
    Call setOutputValue(5,Taverage_Tank)
    Call setOutputValue(6,0.d0)
    Call setOutputValue(7,0.d0)
    Call setOutputValue(8,0.d0)
    Call setOutputValue(9,0.d0)
    Call setOutputValue(10,0.d0)
    Call setOutputValue(11,0.d0)
    Call setOutputValue(12,0.d0)
    Call setOutputValue(13,0.d0)

    Do j=1,N_Thermostats
       Call setOutputValue(13+j,Taverage_Tank)
    EndDo

    Do j=1,N_Nodes
       Call setOutputValue(13+N_Thermostats+j,Tinitial_TankNode(j))
    EndDo

   !Set the Initial Values of the Dynamic Storage Variables
    Do j=1,N_Nodes
       Call SetDynamicArrayInitialValue(j,Tinitial_TankNode(j))
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
       Call initReportValue(1,'Tank Volume',Volume_Tank,'m3')
       Call initReportValue(2,'# of Tank Nodes',dble(N_Nodes),'-')
       Call initReportValue(3,'# of Thermostats',dble(N_Thermostats),'-')
       Call initReportValue(4,'# of Auxiliary Inputs',dble(N_AuxLocations),'-')
    EndIf  

   Return

 EndIf
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!ReRead the Parameters if Another Unit of This Type Has Been Called Last
 If(getIsReReadParameters()) Then
    Volume_Tank = getParameterValue(1)
    Height_Tank = getParameterValue(2)
    N_Nodes=JFIX(getParameterValue(3)+0.1)
    U_Top = getParameterValue(4)
    U_Edge = getParameterValue(5)
    U_Bottom = getParameterValue(6)
    SpecificHeat_TankFluid = getParameterValue(7)
    Density_TankFluid = getParameterValue(8)
    Conductivity_TankFluid = getParameterValue(9)
    FracHeight_Inlet1 = getParameterValue(10)
    FracHeight_Outlet1 = getParameterValue(11)
    FracHeight_Inlet2 = getParameterValue(12)
    FracHeight_Outlet2 = getParameterValue(13)
    N_Thermostats=JFIX(getParameterValue(14)+0.1)
    Do j=1,N_Thermostats
       FracHeight_Tstat(j)=getParameterValue(14+j)
    EndDo
    N_AuxLocations=JFIX(getParameterValue(15+N_Thermostats)+0.1)
    Do j=1,N_AuxLocations
       FracHeight_Aux(j)=getParameterValue(15+N_Thermostats+j)
    EndDo
 EndIf
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Get the Input Values
 T_Flow_in(1)=getInputValue(1)
 Mdot_Flow_in(1)=getInputValue(2)
 T_Flow_in(2)=getInputValue(3)
 Mdot_Flow_in(2)=getInputValue(4)
 T_TopLoss=getInputValue(5)
 T_EdgeLoss=getInputValue(6)
 T_BottomLoss=getInputValue(7)
 
 Do j=1,N_AuxLocations
    Q_AuxiliaryInput(j)=getInputValue(7+j)
 EndDo
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Check the Inputs for Problems (#,ErrorType,Text)
 If(Mdot_Flow_in(1) < 0.) Call FoundBadInput(2,'Fatal','The flow rate through the tank must be greater than or equal to zero.')
 If(Mdot_Flow_in(2) < 0.) Call FoundBadInput(4,'Fatal','The flow rate through the tank must be greater than or equal to zero.')
 If(ErrorFound()) Return
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Calculate parameter dependent values

!Get the nodes for the port inlets and outlets
 Node_Inlet(1)=0
 Node_Inlet(2)=0
 Node_Outlet(1)=0
 Node_Outlet(2)=0
 
 Do j=N_Nodes,1,-1
    Frac_Now=DBLE(N_Nodes-j+1)/DBLE(N_Nodes)
    If((FracHeight_Inlet1<Frac_Now).and.(Node_Inlet(1)==0)) Node_Inlet(1)=j
    If((FracHeight_Inlet2<Frac_Now).and.(Node_Inlet(2)==0)) Node_Inlet(2)=j
    If((FracHeight_Outlet1<Frac_Now).and.(Node_Outlet(1)==0)) Node_Outlet(1)=j
    If((FracHeight_Outlet2<Frac_Now).and.(Node_Outlet(2)==0)) Node_Outlet(2)=j
 EndDo
 If(FracHeight_Inlet1>=1.) Node_Inlet(1)=1
 If(FracHeight_Inlet2>=1.) Node_Inlet(2)=1
 If(FracHeight_Outlet1>=1.) Node_Outlet(1)=1
 If(FracHeight_Outlet2>=1.) Node_Outlet(2)=1

!Set the fraction of the inlet flow to 1 for the inlet node and to 0 otherwise
 Do j=1,N_Nodes
    If(j==Node_Inlet(1)) Then
       Fraction_Inlet(1,j)=1.
    Else
       Fraction_Inlet(1,j)=0.
    EndIf
    
    If(j==Node_Inlet(2)) Then
       Fraction_Inlet(2,j)=1.
    Else
       Fraction_Inlet(2,j)=0.
    EndIf
 EndDo

!Calculate the node containing the thermostats
 Do k=1,N_Thermostats
    Node_Thermostat(k)=0
    Do j=N_Nodes,1,-1
       Frac_Now=DBLE(N_Nodes-j+1)/DBLE(N_Nodes)
       If((FracHeight_Tstat(k)<Frac_Now).and.(Node_Thermostat(k)==0)) Node_Thermostat(k)=j
    EndDo
    If(FracHeight_Tstat(k)>=1.) Node_Thermostat(k)=1
 EndDo

!Calculate the node containing the auxiliary heat input
 Do k=1,N_AuxLocations
    Node_Auxiliary(k)=0
    Do j=N_Nodes,1,-1
       Frac_Now=DBLE(N_Nodes-j+1)/DBLE(N_Nodes)
       If((FracHeight_Aux(k)<Frac_Now).and.(Node_Auxiliary(k)==0)) Node_Auxiliary(k)=j
    EndDo
    If(FracHeight_Aux(k)>=1.) Node_Auxiliary(k)=1
 EndDo

!Calculate the volume of each tank node
 Do j=1,N_Nodes
    Volume_TankNode(j)=Volume_Tank/DBLE(N_Nodes)
 EndDo

!Calculate the radius of the tank
 Radius_Tank=(Volume_Tank/Pi/Height_Tank)**0.5

!Set the capacitance of each tank node
 Do j=1,N_Nodes
    Capacitance_TankNode(j)=Volume_TankNode(j)*Density_TankFluid*SpecificHeat_TankFluid
 EndDo

!Calculate the surface areas for the single node case
 If(N_Nodes==1) Then
    Area_TopSurface(1)=Pi*Radius_Tank*Radius_Tank
    Area_BottomSurface(1)=Pi*Radius_Tank*Radius_Tank
    Area_Edges(1)=2.*Pi*Radius_Tank*Height_Tank
    ConductionArea(1)=Pi*Radius_Tank*Radius_Tank
    L_Conduction(1)=Height_Tank/2.
    
!Calculate the surface areas for the multiple node case
 Else
    Do j=1,N_Nodes
       If(j==1) Then
          Area_TopSurface(j)=Pi*Radius_Tank*Radius_Tank
          Area_BottomSurface(j)=0.
          Area_Edges(j)=2.*Pi*Radius_Tank*Height_Tank/DBLE(N_Nodes)
          ConductionArea(j)=Pi*Radius_Tank*Radius_Tank
          L_Conduction(j)=Height_Tank/DBLE(N_Nodes)
       Else If(j==N_Nodes) Then
          Area_TopSurface(j)=0.
          Area_BottomSurface(j)=Pi*Radius_Tank*Radius_Tank
          Area_Edges(j)=2.*Pi*Radius_Tank*Height_Tank/DBLE(N_Nodes)
          ConductionArea(j)=Pi*Radius_Tank*Radius_Tank
          L_Conduction(j)=Height_Tank/DBLE(N_Nodes)
       Else
          Area_TopSurface(j)=0.
          Area_BottomSurface(j)=0.
          Area_Edges(j)=2.*Pi*Radius_Tank*Height_Tank/DBLE(N_Nodes)
          ConductionArea(j)=Pi*Radius_Tank*Radius_Tank
          L_Conduction(j)=Height_Tank/DBLE(N_Nodes)
       EndIf
    EndDo
 EndIf


!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Get the Initial Values of the Dynamic Variables from the Global Storage Array
 Do j=1,N_Nodes
    Tinitial_TankNode(j)=getDynamicArrayValueLastTimestep(j)
    Tstart_TankNode(j)=getDynamicArrayValueLastTimestep(j)
    Tfinal_TankNode(j)=getDynamicArrayValueLastTimestep(j)
    Taverage_TankNode(j)=getDynamicArrayValueLastTimestep(j)
 EndDo
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Main calculation loop
 Iterations_Max=20
 
!Indicate that the temperatures have not been checked for stability
 Do j=1,N_Nodes
    StabilityChecked(j)=.False.
    Iterations_Tank(j)=1
 EndDo

!Set some initial conditions for the iterative calculations
 Iterations_Tank_Max=1
 CheckingTemperatures=.True.
 Q_EdgeLoss=0.
 Q_BottomLoss=0.
 Q_TopLoss=0.
 Q_Auxiliary_Total=0.
 Q_Stored_Tank=0.
 Q_Delivered_Port=0.
 Q_Delivered_Total=0.

!Start the iterative calculations here - everything above this point is independent of the iterative scheme
 200 Continue

!Reset the differential equation terms AA and BB where  dT/dt=AA*T+BB
 Do j=1,N_Nodes
    AA(j)=0.
    BB(j)=0.
 EndDo

!Set the flow rate for each node from each port
 N_Ports=2
 
 Do i=1,N_Ports
    Do j=1,N_Nodes
       Mdot_Mains(i,j)=Mdot_Flow_in(i)*Fraction_Inlet(i,j)
    EndDo
 EndDo

!Set the inlet temperatures and flows to each tank node from each port
 Do i=1,N_Ports

   !Start at the bottom and works towards the outlet
    Do j=N_Nodes,1,-1
       If(j==Node_Outlet(i)) EXIT
     
       If(j==N_Nodes) Then
          T_Load_In(i,j)=Taverage_TankNode(j)
          Mdot_Load_In(i,j)=0.
          Mdot_Load_Out(i,j)=Mdot_Mains(i,j)
       Else
          T_Load_In(i,j)=Taverage_TankNode(j+1)
          Mdot_Load_In(i,j)=Mdot_Load_Out(i,j+1)
          Mdot_Load_Out(i,j)=Mdot_Mains(i,j)+Mdot_Load_In(i,j)
       EndIf
    EndDo
          
   !Now start at the top and works towards the outlet
    Do j=1,N_Nodes
       If(j==Node_Outlet(i)) EXIT
     
       If(j==1) Then
          T_Load_In(i,j)=Taverage_TankNode(j)
          Mdot_Load_In(i,j)=0.
          Mdot_Load_Out(i,j)=Mdot_Mains(i,j)
       Else
          T_Load_In(i,j)=Taverage_TankNode(j-1)
          Mdot_Load_In(i,j)=Mdot_Load_Out(i,j-1)
          Mdot_Load_Out(i,j)=Mdot_Mains(i,j)+Mdot_Load_In(i,j)
       EndIf
    EndDo
 EndDo

!Handle the single node tank case
 If(N_Nodes==1) Then
    Do i=1,N_Ports
       Mdot_Load_In(i,1)=0.
       Mdot_Load_Out(i,1)=Mdot_Mains(i,1)
    EndDo
 EndIf

!Set the AA and BB terms for the nodal differential equation for the inlet flows
 Do i=1,N_Ports
    Do j=1,N_Nodes
       If(N_Nodes==1) Then
          AA(j)=AA(j)-Mdot_Mains(i,j)*SpecificHeat_TankFluid/Capacitance_TankNode(j)
          BB(j)=BB(j)+Mdot_Mains(i,j)*SpecificHeat_TankFluid*T_Flow_in(i)/Capacitance_TankNode(j)
       Else If(j.NE.Node_Outlet(i)) Then
          AA(j)=AA(j)-Mdot_Load_Out(i,j)*SpecificHeat_TankFluid/Capacitance_TankNode(j)
          BB(j)=BB(j)+(Mdot_Mains(i,j)*SpecificHeat_TankFluid*T_Flow_in(i)+Mdot_Load_In(i,j)*SpecificHeat_TankFluid*T_Load_In(i,j))/Capacitance_TankNode(j)
       Else
          If(j==1) Then
             Mdot_Load_Out(i,j)=Mdot_Flow_in(i)
             Mdot_Load_In(i,j)=Mdot_Load_Out(i,j+1)
             
             T_Load_In(i,j)=Taverage_TankNode(j+1)

             AA(j)=AA(j)-Mdot_Load_Out(i,j)*SpecificHeat_TankFluid/Capacitance_TankNode(j)
             BB(j)=BB(j)+(Mdot_Mains(i,j)*SpecificHeat_TankFluid*T_Flow_in(i)+Mdot_Load_In(i,j)*SpecificHeat_TankFluid*T_Load_In(i,j))/Capacitance_TankNode(j)
          
          Else If(j==N_Nodes) Then
             Mdot_Load_Out(i,j)=Mdot_Flow_in(i)
             Mdot_Load_In(i,j)=Mdot_Load_Out(i,j-1)
             
             T_Load_In(i,j)=Taverage_TankNode(j-1)

             AA(j)=AA(j)-Mdot_Load_Out(i,j)*SpecificHeat_TankFluid/Capacitance_TankNode(j)
             BB(j)=BB(j)+(Mdot_Mains(i,j)*SpecificHeat_TankFluid*T_Flow_in(i)+Mdot_Load_In(i,j)*SpecificHeat_TankFluid*T_Load_In(i,j))/Capacitance_TankNode(j)
          
          Else
             Mdot_Load_Out(i,j)=Mdot_Flow_in(i)
             Mdot_Load_In(i,j)=Mdot_Load_Out(i,j-1)+Mdot_Load_Out(i,j+1)
             
             If((Mdot_Flow_in(i)>0.).AND.((Mdot_Load_Out(i,j-1)+Mdot_Load_Out(i,j+1))>0.)) Then
                T_Load_In(i,j)=(Taverage_TankNode(j-1)*Mdot_Load_Out(i,j-1)+Taverage_TankNode(j+1)*Mdot_Load_Out(i,j+1))/(Mdot_Load_Out(i,j-1)+Mdot_Load_Out(i,j+1))
             Else
                T_Load_In(i,j)=Taverage_TankNode(j)
             EndIf

             AA(j)=AA(j)-Mdot_Load_Out(i,j)*SpecificHeat_TankFluid/Capacitance_TankNode(j)
             BB(j)=BB(j)+(Mdot_Mains(i,j)*SpecificHeat_TankFluid*T_Flow_in(i)+Mdot_Load_Out(i,j-1)*SpecificHeat_TankFluid*Taverage_TankNode(j-1)+Mdot_Load_Out(i,j+1)*SpecificHeat_TankFluid*Taverage_TankNode(j+1))/Capacitance_TankNode(j)
          EndIf
       EndIf
    EndDo
 EndDo

!Set the AA and BB terms for the nodal differential equation for the auxiliary heaters
 Do k=1,N_AuxLocations
    BB(Node_Auxiliary(k))=BB(Node_Auxiliary(k))+Q_AuxiliaryInput(k)/Capacitance_TankNode(Node_Auxiliary(k))
 EndDo

!Set the AA and BB terms for the nodal differential equation for the thermal losses from the top surface
 Do j=1,N_Nodes
    UA_TopSurface=U_Top*Area_TopSurface(j)
    AA(j)=AA(j)-UA_TopSurface/Capacitance_TankNode(j)
    BB(j)=BB(j)+UA_TopSurface*T_TopLoss/Capacitance_TankNode(j)
 EndDo

!Set the AA and BB terms for the nodal differential equation for the thermal losses from the edge surfaces
 Do j=1,N_Nodes
    UA_Edges=U_Edge*Area_Edges(j)
    AA(j)=AA(j)-UA_Edges/Capacitance_TankNode(j)
    BB(j)=BB(j)+UA_Edges*T_EdgeLoss/Capacitance_TankNode(j)
 EndDo

!Set the AA and BB terms for the nodal differential equation for the thermal losses from the bottom surface
 Do j=1,N_Nodes
    UA_BottomSurface=U_Bottom*Area_BottomSurface(j)
    AA(j)=AA(j)-UA_BottomSurface/Capacitance_TankNode(j)
    BB(j)=BB(j)+UA_BottomSurface*T_BottomLoss/Capacitance_TankNode(j)
 EndDo

!Set the AA and BB terms for the nodal differential equation for conduction between nodes
 If (N_Nodes > 1) Then
     Do j=1,N_Nodes
        If(j==1) Then
           AA(j)=AA(j)-Conductivity_TankFluid*ConductionArea(j)/L_Conduction(j)/Capacitance_TankNode(j)
           BB(j)=BB(j)+Conductivity_TankFluid*ConductionArea(j)/L_Conduction(j)*Taverage_TankNode(j+1)/Capacitance_TankNode(j)
        Else If(j==N_Nodes) Then
           AA(j)=AA(j)-Conductivity_TankFluid*ConductionArea(j-1)/L_Conduction(j-1)/Capacitance_TankNode(j)
           BB(j)=BB(j)+Conductivity_TankFluid*ConductionArea(j-1)/L_Conduction(j-1)*Taverage_TankNode(j-1)/Capacitance_TankNode(j)
        Else
           AA(j)=AA(j)-Conductivity_TankFluid*ConductionArea(j)/L_Conduction(j)/Capacitance_TankNode(j)-Conductivity_TankFluid*ConductionArea(j-1)/L_Conduction(j-1)/Capacitance_TankNode(j)
           BB(j)=BB(j)+Conductivity_TankFluid*ConductionArea(j)/L_Conduction(j)*Taverage_TankNode(j+1)/Capacitance_TankNode(j)+Conductivity_TankFluid*ConductionArea(j-1)/L_Conduction(j-1)*Taverage_TankNode(j-1)/Capacitance_TankNode(j)
        EndIf
     EndDo
 EndIf

!Determine the final and average tank node temperatures
 Do j=1,N_Nodes
    If(AA(j)==0.) Then
       Tfinal_TankNode_New(j)=Tinitial_TankNode(j)+BB(j)*Timestep
       Taverage_TankNode_New(j)=Tinitial_TankNode(j)+BB(j)*Timestep/2.
    Else
       Tfinal_TankNode_New(j)=(Tinitial_TankNode(j)+BB(j)/AA(j))*DEXP(AA(j)*Timestep)-BB(j)/AA(j)
       Taverage_TankNode_New(j)=(Tinitial_TankNode(j)+BB(j)/AA(j))*(DEXP(AA(j)*Timestep)-1.)/AA(j)/Timestep-BB(j)/AA(j)
    EndIf
 EndDo

!See If the tank node temperatures have converged
 Converged_Tank=.TRUE.
 Do j=1,N_Nodes
    If((DABS(Taverage_TankNode_New(j)-Taverage_TankNode(j))>ConvergenceCriteria).AND.(Iterations_Tank(j)<=Iterations_Max)) Then
       Converged_Tank=.FALSE.
       Iterations_Tank(j)=Iterations_Tank(j)+1
       Iterations_Tank_Max=MAX(Iterations_Tank_Max,Iterations_Tank(j))
    EndIf
 EndDo
          
 If(Converged_Tank) Then
    If(Iterations_Tank_Max>=Iterations_Max) Then
       IterationLimitReached_Tank=.TRUE.
    Else
       IterationLimitReached_Tank=.FALSE.
    EndIf

    Do j=1,N_Nodes
       Taverage_TankNode(j)=Taverage_TankNode_New(j)
       Tfinal_TankNode(j)=Tfinal_TankNode_New(j)
    EndDo
 Else
    Do j=1,N_Nodes
       Taverage_TankNode(j)=Taverage_TankNode_New(j)
       Tfinal_TankNode(j)=Tfinal_TankNode_New(j)
    EndDo
         
    GoTo 200
 EndIf
 
!Calculate the average temperatures
 Taverage_Tank=0.
 Do j=1,N_Nodes
    Taverage_Tank=Taverage_Tank+Taverage_TankNode(j)/DBLE(N_Nodes)
 EndDo

!Calculate the tank energy flows
 Do j=1,N_Nodes
    UA_Edges=U_Edge*Area_Edges(j)
    Q_EdgeLoss=Q_EdgeLoss+UA_Edges*(Taverage_TankNode(j)-T_EdgeLoss)
    UA_BottomSurface=U_Bottom*Area_BottomSurface(j)
    Q_BottomLoss=Q_BottomLoss+UA_BottomSurface*(Taverage_TankNode(j)-T_BottomLoss)
    UA_TopSurface=U_Top*Area_TopSurface(j)
    Q_TopLoss=Q_TopLoss+UA_TopSurface*(Taverage_TankNode(j)-T_TopLoss)
    Q_Stored_Tank=Q_Stored_Tank+Capacitance_TankNode(j)*(Tfinal_TankNode(j)-Tstart_TankNode(j))/TimeStep
         
    Do i=1,N_Ports
       Q_Delivered_Port(i)=Q_Delivered_Port(i)+Mdot_Load_Out(i,j)*SpecificHeat_TankFluid*Taverage_TankNode(j)-Mdot_Mains(i,j)*SpecificHeat_TankFluid*T_Flow_in(i)-Mdot_Load_In(i,j)*SpecificHeat_TankFluid*T_Load_In(i,j)
    EndDo
 EndDo
    
 Do i=1,N_AuxLocations
    Q_Auxiliary_Total=Q_Auxiliary_Total+Q_AuxiliaryInput(i)
 EndDo

 Do i=1,N_Ports
    Q_Delivered_Total=Q_Delivered_Total+Q_Delivered_Port(i)
 EndDo

!Calculate the energy balance errors
 EnergyBalance_Numerator_Tank=Q_Stored_Tank+Q_EdgeLoss+Q_BottomLoss+Q_TopLoss+Q_Delivered_Total-Q_Auxiliary_Total
 EnergyBalance_Denominator_Tank=DABS(Q_TopLoss)+DABS(Q_Delivered_Total)+DABS(Q_EdgeLoss)+DABS(Q_BottomLoss)+DABS(Q_Auxiliary_Total)
 EnergyBalance_Error_Tank=DABS(EnergyBalance_Numerator_Tank)/DMAX1(1.0,EnergyBalance_Denominator_Tank)*100.
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Perform an instantaneous adiabatic mixing to eliminate temperature inversions
 5150 Continue

 Do j=1,N_Nodes-1
    If(Tfinal_TankNode(j)<Tfinal_TankNode(j+1)) Goto 5165
 EndDo

!Update the dynamic variables
 Do j=1,N_Nodes
    Call SetDynamicArrayValueThisIteration(j,Tfinal_TankNode(j))
 EndDo

 Goto 300

 5165 Continue

 T_Mixed = 0.
 Capacitance_Mixed = 0.
 Do m=j,N_Nodes
    T_Mixed = T_Mixed + Tfinal_TankNode(m)*Capacitance_TankNode(m)
    Capacitance_Mixed = Capacitance_Mixed + Capacitance_TankNode(m)
    If(m==N_Nodes) Goto 5185
    If(T_Mixed/Capacitance_Mixed>Tfinal_TankNode(m+1)) Goto 5185
 EndDo

 5185 Continue
 
 T_Mixed = T_Mixed/Capacitance_Mixed
      
 Do k=j,m
    If(AA(k)==0.) Then
       Finalfactor_Mixing = TimeStep/Capacitance_TankNode(k)
       Averagefactor_Mixing = Finalfactor_Mixing/2.
    Else
       Finalfactor_Mixing=(DEXP(AA(k)*TimeStep)-1.)/AA(k)/Capacitance_TankNode(k)
       Averagefactor_Mixing=((DEXP(AA(k)*TimeStep)-1.)/AA(k)/TimeStep-1.)/AA(k)/Capacitance_TankNode(k)
    EndIf
         
    Q_AdiabaticMixing=(T_Mixed-Tfinal_TankNode(k))/Finalfactor_Mixing
         
    Tfinal_TankNode(k)=T_Mixed
    Taverage_TankNode(k)=Taverage_TankNode(k)+Q_AdiabaticMixing*Averagefactor_Mixing
 EndDo
    
 Goto 5150
!-----------------------------------------------------------------------------------------------------------------------

!-----------------------------------------------------------------------------------------------------------------------
!Set the Outputs from this Model (#,Value)
300 Continue
    
 Call setOutputValue(1,Taverage_TankNode(Node_Outlet(1)))
 Call setOutputValue(2,Mdot_Flow_in(1))
 Call setOutputValue(3,Taverage_TankNode(Node_Outlet(2)))
 Call setOutputValue(4,Mdot_Flow_in(2))
 Call setOutputValue(5,Taverage_Tank)
 Call setOutputValue(6,Q_Delivered_Port(1))
 Call setOutputValue(7,Q_Delivered_Port(2))
 Call setOutputValue(8,Q_TopLoss)
 Call setOutputValue(9,Q_EdgeLoss)
 Call setOutputValue(10,Q_BottomLoss)
 Call setOutputValue(11,Q_Auxiliary_Total)
 Call setOutputValue(12,Q_Stored_Tank)
 Call setOutputValue(13,EnergyBalance_Error_Tank)

 Do j=1,N_Thermostats
    Call setOutputValue(13+j,Taverage_TankNode(Node_Thermostat(j)))
 EndDo

 Do j=1,N_Nodes
    Call setOutputValue(13+N_Thermostats+j,Taverage_TankNode(j))
 EndDo
!-----------------------------------------------------------------------------------------------------------------------

 Return
 End
