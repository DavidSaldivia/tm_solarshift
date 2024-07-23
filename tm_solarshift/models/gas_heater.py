from __future__ import annotations
import numpy as np
import pandas as pd
from typing import TYPE_CHECKING
from tm_solarshift.constants import DIRECTORY
from tm_solarshift.utils.units import (
    Variable,
    conversion_factor as CF,
    Water,
)

from tm_solarshift.models.dewh import HWTank

if TYPE_CHECKING:
    from tm_solarshift.general import Simulation

FILES_MODEL_SPECS = DIRECTORY.FILES_MODEL_SPECS

#-------------------------
class GasHeaterInstantaneous():
    def __init__(self):
        
        # description
        self.name = "Gas heater instantaneous (no storage)."
        self.label = "gas_instant"
        self.model = "-"
        self.cost = Variable(np.nan, "AUD")

        # Default data from:
        # https://www.rheem.com.au/rheem/products/Residential/Gas-Continuous-Flow/Continuous-Flow-%2812---27L%29/Rheem-12L-Gas-Continuous-Flow-Water-Heater-%3A-50%C2%B0C-preset/p/876812PF#collapse-1-2-1
        # Data from model Rheim 20
        
        #heater
        self.nom_power = Variable(157., "MJ/hr")
        self.flow_water = Variable(20., "L/min")
        self.deltaT_rise = Variable(25., "dgrC")
        self.heat_value = Variable(47.,"MJ/kg_gas")
        
        #tank
        self.vol = Variable(0., "m3")
        self.thermal_cap = Variable(0., "kWh")
        self.fluid = Water()

        #control
        self.temp_consump = Variable(45.0, "degC")

        #finance
        self.cost = Variable(np.nan, "AUD")
        self.model = "-"

    @property
    def eta(self) -> Variable:
        nom_power = self.nom_power.get_value("MJ/hr")
        deltaT_rise = self.deltaT_rise.get_value("dgrC")
        flow_w = self.flow_water.get_value("m3/s")
        cp_w = self.fluid.cp.get_value("J/kg-K")
        rho_w = self.fluid.rho.get_value("kg/m3")
        HW_energy = (flow_w * rho_w * cp_w) * deltaT_rise * CF("W", "MJ/hr")  #[MJ/hr]
        return Variable(HW_energy / nom_power, "-")

    @classmethod
    def from_model_file(
        cls,
        file_path: str = FILES_MODEL_SPECS["gas_instant"],
        model:str = "",
        ):
        df = pd.read_csv(file_path, index_col=0)
        specs = pd.Series(df.loc[model])
        units = pd.Series(df.loc["units"])
        output = cls()
        for (lbl,value) in specs.items():
            unit = units[str(lbl)]
            try:
                value = float(value)
            except:
                pass    
            setattr(output, str(lbl), Variable(value, unit) )
        return output
    
    def run_thermal_model(
        self,
        ts: pd.DataFrame,
        verbose: bool = False,
    ) -> tuple[pd.DataFrame, dict[str, float]]:
        
        ts_index = pd.to_datetime(ts.index)
        DAYS = len(np.unique(ts_index.date))
        freq = ts_index.freq
        if freq is None:
            raise IndexError("timeseries ts has no proper Index")
        STEP_h = freq.n * CF("min", "hr")

        hw_flow = ts["m_HWD"]
        temp_amb_avg = ts["temp_amb"].mean()
        temp_mains_avg = ts["temp_mains"].mean()

        nom_power = self.nom_power.get_value("MJ/hr")
        deltaT_rise = self.deltaT_rise.get_value("dgrC")
        flow_water = self.flow_water.get_value("L/min")

        #Assuming pure methane for gas
        heat_value = self.heat_value.get_value("MJ/kg_gas")
        cp_water = self.fluid.cp.get_value("J/kg-K")
        rho_water = self.fluid.rho.get_value("kg/m3")
        eta = self.eta.get_value("-")

        # #Calculations
        flow_gas = nom_power / heat_value         #[kg/hr]
        HW_energy = ((flow_water / CF("min", "s") * CF("L", "m3") )
                    * rho_water * cp_water 
                    * deltaT_rise
                    * CF("W", "MJ/hr")
                    )  #[MJ/hr]

        specific_energy = (nom_power / flow_water * CF("min", "hr") * CF("MJ", "kWh")) #[kWh/L]
        df_tm = pd.DataFrame(index = ts.index)
        df_tm["m_HWD"] = hw_flow
        df_tm["eta"] = eta
        df_tm["heater_power"] = specific_energy * hw_flow * CF("MJ", "kJ")    #[kJ/h]
        df_tm["heater_heat"] = eta * df_tm["heater_power"]    #[kJ/h]

        # specific_emissions = (kgCO2_TO_kgCH4 
        #                 / (heat_value * CF("MJ", "kWh"))
        #                 / eta
        #                 ) #[kg_CO2/kWh_thermal]

        # E_HWD = specific_energy * hw_flow * STEP_h                  #[kWh]
        # E_HWD_acum = E_HWD.sum()                                    #[kWh]


        # emissions = E_HWD * specific_emissions * CF("kg", "ton")    #[tonCO2]
        # emissions_total = emissions.sum()                           #[tonCO2_annual]
        # emissions_marginal = emissions.sum()                        #[tonCO2_annual]

        # heater_heat_acum = E_HWD_acum / eta
        # m_HWD_avg = (hw_flow * STEP_h).sum() / DAYS

        # out_overall = {
        #     "heater_heat_acum": heater_heat_acum,
        #     "heater_perf_avg": eta,
        #     "E_HWD_acum": E_HWD_acum,
        #     "m_HWD_avg": m_HWD_avg,
        #     "temp_amb_avg": temp_amb_avg,
        #     "temp_mains_avg": temp_mains_avg,
        #     "emissions_total": emissions_total,
        #     "emissions_marginal": emissions_marginal,
        #     "solar_ratio": 0.0,
        #     "t_SOC0": 0.0,

        #     "heater_power_acum": np.nan,
        #     "E_losses": np.nan,
        #     "eta_stg": np.nan,
        #     "cycles_day": np.nan,
        #     "SOC_avg": np.nan,
        #     "SOC_min": np.nan,
        #     "SOC_025": np.nan,
        #     "SOC_050": np.nan,
        # }
        return df_tm
    
    def postproc(self, df_tm: pd.DataFrame) -> dict[str,float]:

        kgCO2_TO_kgCH4 = 44. / 16.
        nom_power = self.nom_power.get_value("MJ/hr")
        deltaT_rise = self.deltaT_rise.get_value("dgrC")
        flow_water = self.flow_water.get_value("L/min")
        heat_value = self.heat_value.get_value("MJ/kg_gas")
        cp_water = self.fluid.cp.get_value("J/kg-K")
        rho_water = self.fluid.rho.get_value("kg/m3")
        eta = self.eta.get_value("-")
        
        ts_index = pd.to_datetime(df_tm.index)
        DAYS = len(np.unique(ts_index.date))
        freq = ts_index.freq
        if freq is None:
            raise IndexError("timeseries ts has no proper Index")
        STEP_h = freq.n * CF("min", "hr")
        hw_flow = df_tm["m_HWD"]

        specific_energy = (nom_power / flow_water * CF("min", "hr") * CF("MJ", "kWh")) #[kWh/L]
        specific_emissions = (kgCO2_TO_kgCH4 
                / (heat_value * CF("MJ", "kWh"))
                / eta
                ) #[kg_CO2/kWh_thermal]

        E_HWD = specific_energy * hw_flow * STEP_h                  #[kWh]
        E_HWD_acum = E_HWD.sum()                                    #[kWh]

        emissions = E_HWD * specific_emissions * CF("kg", "ton")    #[tonCO2]
        emissions_total = emissions.sum()                           #[tonCO2_annual]
        emissions_marginal = emissions.sum()                        #[tonCO2_annual]

        heater_heat_acum = E_HWD_acum / eta
        m_HWD_avg = (hw_flow * STEP_h).sum() / DAYS
        overall_th = {
            "heater_heat_acum": heater_heat_acum,
            "heater_perf_avg": eta,
            "E_HWD_acum": E_HWD_acum,
            "m_HWD_avg": m_HWD_avg,
            # "temp_amb_avg": temp_amb_avg,
            # "temp_mains_avg": temp_mains_avg,
            "emissions_total": emissions_total,
            "emissions_marginal": emissions_marginal,
            "solar_ratio": 0.0,
            "t_SOC0": 0.0,

            "heater_power_acum": np.nan,
            "E_losses": np.nan,
            "eta_stg": np.nan,
            "cycles_day": np.nan,
            "SOC_avg": np.nan,
            "SOC_min": np.nan,
            "SOC_025": np.nan,
            "SOC_050": np.nan,
        }
        return overall_th



class GasHeaterStorage(HWTank):
    def __init__(self):
        
        super().__init__()
        # description
        self.name = "Gas heater with storage tank."
        self.label = "gas_storage"
        self.model = "-"
        self.cost = Variable(np.nan, "AUD")
        
        # Gas heater data are from GasInstantaneous:
        # https://www.rheem.com.au/rheem/products/Residential/Gas-Continuous-Flow/Continuous-Flow-%2812---27L%29/Rheem-12L-Gas-Continuous-Flow-Water-Heater-%3A-50%C2%B0C-preset/p/876812PF#collapse-1-2-1
        # Data from model Rheim 20
        # Tank data are from ResistiveSingle default

        # heater
        self.nom_power = Variable(157., "MJ/hr")
        self.flow_water = Variable(20., "L/min")
        self.deltaT_rise = Variable(25., "dgrC")
        self.heat_value = Variable(47.,"MJ/kg_gas")

    @property
    def eta(self) -> Variable:        
        nom_power = self.nom_power.get_value("MJ/hr")
        deltaT_rise = self.deltaT_rise.get_value("dgrC")
        flow_w = self.flow_water.get_value("m3/s")
        cp_w = self.fluid.cp.get_value("J/kg-K")
        rho_w = self.fluid.rho.get_value("kg/m3")
        HW_energy = (flow_w * rho_w * cp_w) * deltaT_rise * CF("W", "MJ/hr")  #[MJ/hr]
        return Variable(HW_energy / nom_power, "-")
    @eta.setter
    def eta(self, value): ...
    
    @classmethod
    def from_model_file(
        cls,
        file_path: str = FILES_MODEL_SPECS["gas_storage"],
        model:str = "",
        ):
        df = pd.read_csv(file_path, index_col=0)
        specs = pd.Series(df.loc[model])
        units = pd.Series(df.loc["units"])
        
        output = cls()
        for (lbl,value) in specs.items():
            unit = units[str(lbl)]
            try:
                value = float(value)
            except:
                pass          
            setattr(output, str(lbl), Variable(value, unit) )
        return output
    

    def run_thermal_model(
            self,
            ts: pd.DataFrame,
            verbose: bool = False,
    ) -> pd.DataFrame:
        from tm_solarshift.models import (trnsys, postprocessing)
        trnsys_dewh = trnsys.TrnsysDEWH(DEWH=self, ts=ts)
        df_tm = trnsys_dewh.run_simulation(verbose=verbose)
        return df_tm


#--------------------------------
def storage_fixed_eta(
        sim: Simulation,
        ts: pd.DataFrame,
        verbose: bool = False,
) -> tuple[pd.DataFrame,dict[str, float]]:

    from tm_solarshift.models import (trnsys, postprocessing)
    DEWH: GasHeaterStorage = sim.DEWH
    kgCO2_TO_kgCH4 = (44./16.)          #Assuming pure methane for gas
    heat_value = DEWH.heat_value.get_value("MJ/kg_gas")
    eta = sim.DEWH.eta.get_value("-")

    trnsys_dewh = trnsys.TrnsysDEWH(DEWH=DEWH, ts=ts)
    df_tm = trnsys_dewh.run_simulation(verbose=verbose)
    out_overall = postprocessing.thermal_analysis(sim, ts, df_tm)
    sp_emissions = (kgCO2_TO_kgCH4 / (heat_value * CF("MJ", "kWh")) / eta ) #[kg_CO2/kWh_thermal]

    emissions_total = out_overall["heater_heat_acum"] * sp_emissions * CF("kg", "ton")    #[tonCO2_annual]
    emissions_marginal = emissions_total
    
    out_overall["emissions_total"] = emissions_total
    out_overall["emissions_marginal"] = emissions_marginal
    out_overall["solar_ratio"] = 0.0
    return (df_tm, out_overall)
