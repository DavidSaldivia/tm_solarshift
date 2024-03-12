# Hot Water Tank TRNSYS code

In TRNSYS the Types (the objects of the software) are written in FORTRAN.
Type 158 is a generic hot water tank with auxiliary heaters (electric) and up to two set of ports (input/output)

The code has 763 lines of code. The following is a description of that code in terms of steps, loops and calculations.

## Main steps
The following are a list of main step comments in the FORTRAN file.

### Preparation and error checking
1. (46) Get the Global Trnsys Simulation Variables
2. (54) Set the Version Number for This Type (not relevant)
3. (62) Do Any Last Call Manipulations Here
4. (69) Perform Any "After Convergence" Manipulations That May Be Required at the End of Each Timestep
5. (87) Do All of the "Very First Call of the Simulation Manipulations" Here
    !Get the critical parameters and check them
    !Set the Correct Input and Output Variable Types
    ! Set up this Type's entry in the SSR
6. (155) Do All of the First Timestep Manipulations Here - There Are No Iterations at the Intial Time
    !Read in the Values of the Parameters from the Input File and Check for Problems
    !Get the initial tank temperatures
    !Set the Initial Values of the Outputs
    !Set the Initial Values of the Dynamic Storage Variables
    !Initialize SSR variables
7. (279) ReRead the Parameters if Another Unit of This Type Has Been Called Last
8. (306) Get the Input Values
9. (321) Check the Inputs for Problems (#,ErrorType,Text)

### Pre-calculations
11. (328) Calculate parameter dependent values
    a. (330) !Get the nodes for the port inlets and outlets
    b. (348) !Set the fraction of the inlet flow to 1 for the inlet node and to 0 otherwise
    c. (363) !Calculate the node containing the thermostats
    d. (373) !Calculate the node containing the auxiliary heat input
    e. (383) !Calculate the volume of each tank node
    f. (388) !Calculate the radius of the tank
    g. (391) !Set the capacitance of each tank node
    h. (396) !Calculate the surface areas for the single node case
    i. (404) !Calculate the surface areas for the multiple node case
12. (433) Get the Initial Values of the Dynamic Variables from the Global Storage Array

### Iterative Loop
13. (443) Main calculation loop
    !Indicate that the temperatures have not been checked for stability
    !Set some initial conditions for the iterative calculations
14. (463) !Start the iterative calculations here - everything above this point is independent of the iterative scheme
    a. (466) !Reset the differential equation terms AA and BB where  dT/dt=AA*T+BB
    b. (472) !Set the flow rate for each node from each port
    c. (481) !Set the inlet temperatures and flows to each tank node from each port
        !Start at the bottom and works towards the outlet
        !Now start at the top and works towards the outlet
    d. (515) !Handle the single node tank case
    e. (523) !Set the AA and BB terms for the nodal differential equation for the inlet flows
    f. (568) !Set the AA and BB terms for the nodal differential equation for the auxiliary heaters
    g. (573) !Set the AA and BB terms for the nodal differential equation for the thermal losses from the top surface
    h. (580) !Set the AA and BB terms for the nodal differential equation for the thermal losses from the edge surfaces
    i. (587) !Set the AA and BB terms for the nodal differential equation for the thermal losses from the bottom surface
    j. (594) !Set the AA and BB terms for the nodal differential equation for conduction between nodes
    k. (610) !Determine the final and average tank node temperatures
    l. (621) !See If the tank node temperatures have converged

### Prepare output and correct temperature inversion
15. (651) !Calculate the average temperatures
16. (657) !Calculate the tank energy flows
17. (658) !Calculate the energy balance errors
18. (687) !Perform an instantaneous adiabatic mixing to eliminate temperature inversions
    !Update the dynamic variables

### Output
19. (735) !Set the Outputs from this Model (#,Value)
