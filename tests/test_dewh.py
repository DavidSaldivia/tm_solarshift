import pandas as pd
import pytest

from tm_solarshift.general import Simulation
from tm_solarshift.models.trnsys import TrnsysDEWH
from tm_solarshift.constants import SIMULATIONS_IO
from tm_solarshift.models.dewh import (DEWH, HWTank, ResistiveSingle, HeatPump)
from tm_solarshift.models.solar_thermal import SolarThermalElecAuxiliary
from tm_solarshift.models.gas_heater import (GasHeaterInstantaneous, GasHeaterStorage)
from tempfile import TemporaryDirectory

from tm_solarshift.utils.units import Variable

@pytest.mark.parametrize("heater_type, model", [
    (ResistiveSingle, "491315"),
    (GasHeaterInstantaneous, "874A26NF"),
    (HeatPump, "REHP-CO2-315GL"),
    (SolarThermalElecAuxiliary,"511325"),
    (GasHeaterStorage,"347170N0"),
])
def test_dewh_from_catalog(heater_type: DEWH, model):
    heater = heater_type.from_model_file(model=model)
    assert type(heater) == heater_type


@pytest.mark.parametrize("heater_type", [
    ResistiveSingle, HeatPump, GasHeaterStorage, SolarThermalElecAuxiliary
])
def test_dewh_check_model_sim_settings(heater_type: HWTank):
    "this test check if the mode can be run"
    
    heater = heater_type()
    
    sim = Simulation()
    ts_index = sim.time_params.idx
    cols = SIMULATIONS_IO.TS_COLUMNS_ALL
    if isinstance(heater, SolarThermalElecAuxiliary):
        cols = cols + ["plane_irrad", "FR_ta", "FR_UL", "heat_capacity"]

    ts_empty = pd.DataFrame(index=ts_index, columns=cols)
    trnsys_dewh = TrnsysDEWH(DEWH=heater, ts=ts_empty)
    with TemporaryDirectory() as tmpdir:
        trnsys_dewh.tempDir = tmpdir
        trnsys_dewh.create_simulation_files()
    assert True
