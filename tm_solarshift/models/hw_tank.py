from __future__ import annotations
import numpy as np

from tm_solarshift.constants import DIRECTORY
from tm_solarshift.utils.units import (Variable, Water)
# from tm_solarshift.models.dewh import HWTank

FILES_MODEL_SPECS = DIRECTORY.FILES_MODEL_SPECS

class HWTank():
    def __init__(self):
        self.label = "hwtank"
        self.nom_power = Variable(None, "W")
        self.nom_power_th = Variable(None, "W")
        self.eta = Variable(None, "-")

        # tank geometry and losses
        self.vol = Variable(0.315,"m3")
        self.height = Variable(1.45, "m")  # It says 1.640 in specs, but it is external height, not internal
        self.height_inlet = Variable(0.113, "m")
        self.height_outlet = Variable(1.317, "m")
        self.height_heater = Variable(0.103, "m")
        self.height_thermostat = Variable(0.103, "m")
        self.U = Variable(0.9, "W/m2-K")
        self.fluid = Water()

        #numerical simulation
        self.nodes = 10     # Tank nodes. DO NOT CHANGE, unless TRNSYS layout is changed too!
        self.temps_ini = 3  # [-] Initial temperature of the tank. Check trnsys.editing_dck_tank() for options

        # control
        self.temp_max = Variable(65.0, "degC")  #Maximum temperature in the tank
        self.temp_deadband = Variable(10.0, "degC") # Dead band for max temp control
        self.temp_min = Variable(45.0, "degC")  # Minimum temperature in the tank
        self.temp_consump = Variable(45.0, "degC") #Consumption temperature
    
    @property
    def thermal_cap(self) -> Variable:
        return tank_thermal_capacity(self)
    @property
    def diam(self) -> Variable:
        return tank_diameter(self)
    @property
    def area_loss(self) -> Variable:
        return tank_area_loss(self)
    @property
    def temp_high_control(self) -> Variable:
        return tank_temp_high_control(self)


def tank_thermal_capacity(tank: HWTank) -> Variable:
    vol = tank.vol.get_value("m3")
    rho = tank.fluid.rho.get_value("kg/m3")
    cp = tank.fluid.cp.get_value("J/kg-K")
    temp_max = tank.temp_max.get_value("degC")
    temp_min = tank.temp_min.get_value("degC")
    thermal_cap = vol * (rho * cp) * (temp_max - temp_min) / 3.6e6
    return Variable( thermal_cap, "kWh")

def tank_diameter(tank: HWTank) -> Variable:
    vol = tank.vol.get_value("m3")
    height = tank.height.get_value("m")
    diam = (4 * vol / np.pi / height) ** 0.5
    return Variable( diam , "m" )

def tank_area_loss(tank: HWTank) -> Variable:
    diam = tank.diam.get_value("m")
    height = tank.height.get_value("m")
    area_loss = np.pi * diam * (diam / 2 + height)
    return Variable( area_loss, "m2" ) 

def tank_temp_high_control(tank: HWTank) -> Variable:
    temp_max = tank.temp_max.get_value("degC")
    temp_deadband = tank.temp_deadband.get_value("degC")
    temp_high_control = temp_max - temp_deadband / 2.0
    return Variable(temp_high_control, "degC")

# class Control():
#     def __init__(self):
#         self.temp_max = Variable(65.0, "degC")  #Maximum temperature in the tank
#         self.temp_deadband = Variable(10.0, "degC") # Dead band for max temp control
#         self.temp_min = Variable(45.0, "degC")  # Minimum temperature in the tank
#         self.temp_consump = Variable(45.0, "degC") #Consumption temperature