from __future__ import annotations
import pandas as pd
from typing import Protocol, Self

from tm_solarshift.utils.units import Variable, Water

# Protocols for DEWH
class DEWH(Protocol):
    @classmethod
    def from_model_file(cls, file_path: str, model: str) -> Self:
        ...
    def run_thermal_model(self, ts: pd.DataFrame, verbose: bool) -> pd.DataFrame:
        ...


# # Protocols for DEWH
# class TrnsysCompatibleDEWH(Protocol):
#     label: str
#     vol: Variable
#     height: Variable
#     height_inlet: Variable
#     height_outlet: Variable
#     height_heater: Variable
#     height_thermostat: Variable
#     U: Variable

#     #numerical simulation
#     fluid: Water
#     nodes: int     # Tank nodes. DO NOT CHANGE, unless TRNSYS layout is changed too!

#     # control
#     temp_max: Variable
#     temp_deadband: Variable
#     temp_min: Variable

#     @property
#     def tank_thermal_cap(self) -> Variable:
#         ...
#     @property
#     def tank_diam(self) -> Variable:
#         ...
#     @property
#     def tank_area_loss(self) -> Variable:
#         ...
#     @property
#     def tank_temp_high_control(self) -> Variable:
#         ...



