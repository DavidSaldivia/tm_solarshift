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
