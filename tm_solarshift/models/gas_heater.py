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
        specs = df.loc[model]
        units = df.loc["units"]
        
        output = cls()
        for (lbl,value) in specs.items():
            unit = units[lbl]
            try:
                value = float(value)
            except:
                pass          
            setattr(output, lbl, Variable(value, unit) )
        return output
    
    def run_thermal_model(
        self,
        ts: pd.DataFrame,
        verbose: bool = False,
    ) -> tuple[pd.DataFrame, dict[str, float]]:
        
        hw_flow = ts["m_HWD"]
        temp_amb_avg = ts["temp_amb"].mean()
        temp_mains_avg = ts["temp_mains"].mean()

        ts_index = pd.to_datetime(ts.index)
        DAYS = len(np.unique(ts_index.date))
        STEP_h = ts_index.freq.n * CF("min", "hr")

        kgCO2_TO_kgCH4 = 44. / 16.

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
        out_all = pd.DataFrame(index = ts.index)
        out_all["m_HWD"] = hw_flow
        out_all["eta"] = eta
        out_all["heater_power"] = specific_energy * hw_flow * CF("MJ", "kJ")    #[kJ/h]

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

        out_overall = {
            "heater_heat_acum": heater_heat_acum,
            "heater_perf_avg": eta,
            "E_HWD_acum": E_HWD_acum,
            "m_HWD_avg": m_HWD_avg,
            "temp_amb_avg": temp_amb_avg,
            "temp_mains_avg": temp_mains_avg,
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
        return (out_all, out_overall)
#-------------------------
class GasHeaterStorage():
    def __init__(self):

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

        # tank
        self.vol = Variable(0.315,"m3")
        self.height = Variable(1.45, "m")  # It says 1.640 in specs, but it is external height, not internal
        self.height_inlet = Variable(0.113, "m")
        self.height_outlet = Variable(1.317, "m")
        self.height_heater = Variable(0.103, "m")
        self.height_thermostat = Variable(0.103, "m")
        self.U = Variable(0.9, "W/m2-K")
        self.nodes = 10     # Tank nodes. DO NOT CHANGE, unless TRNSYS layout is changed too!
        self.temps_ini = 3  # [-] Initial temperature of the tank. Check editing_dck_tank() below for the options
        self.fluid = Water()

        # control
        self.temp_max = Variable(63.0, "degC")  #Maximum temperature in the tank
        self.temp_min = Variable(45.0,"degC")  # Minimum temperature in the tank
        self.temp_high_control = Variable(59.0, "degC")  #Temperature to for control
        self.temp_consump = Variable(45.0, "degC") #Consumption temperature
        self.temp_deadband = Variable(10, "degC")

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
        file_path: str = FILES_MODEL_SPECS["gas_storage"],
        model:str = "",
        ):
        
        df = pd.read_csv(file_path, index_col=0)
        specs = pd.Series(df.loc[model])
        units = pd.Series(df.loc["units"])
        
        output = cls()
        for (lbl,value) in specs.items():
            unit = units[lbl]
            try:
                value = float(value)
            except:
                pass          
            setattr(output, lbl, Variable(value, unit) )
        return output
    
    @property
    def thermal_cap(self):
        from tm_solarshift.models.dewh import tank_thermal_capacity
        return tank_thermal_capacity(self)
    @property
    def diam(self):
        from tm_solarshift.models.dewh import tank_diameter
        return tank_diameter(self)
    @property
    def area_loss(self):
        from tm_solarshift.models.dewh import tank_area_loss
        return tank_area_loss(self)
    
    # def run_thermal_model(
    #         self,
    #         ts: pd.DataFrame,
    #         verbose: bool = False,
    # ) -> tuple[pd.DataFrame,dict[str, float]]:
        
    #     from tm_solarshift.models import (trnsys, postprocessing)
    #     kgCO2_TO_kgCH4 = 44./16.
    #     heat_value = self.heat_value.get_value("MJ/kg_gas")
    #     eta = self.eta.get_value("-")

    #     trnsys_dewh = trnsys.TrnsysDEWH(DEWH=self, ts=ts)
    #     df_tm = trnsys_dewh.run_simulation(ts, verbose=verbose)

    #     # out_overall = postprocessing.annual_postproc(sim, ts, out_all)
    #     # sp_emissions = (kgCO2_TO_kgCH4 / (heat_value * CF("MJ", "kWh")) / eta )             #[kg_CO2/kWh_thermal]

    #     # emissions_total = out_overall["heater_heat_acum"] * sp_emissions * CF("kg", "ton")    #[tonCO2_annual]
    #     # emissions_marginal = emissions_total
        
    #     # out_overall["emissions_total"] = emissions_total
    #     # out_overall["emissions_marginal"] = emissions_marginal
    #     # out_overall["solar_ratio"] = 0.0

    #     return df_tm


#--------------------------------
def storage_fixed_eta(
        sim: Simulation,
        ts: pd.DataFrame,
        verbose: bool = False,
) -> tuple[pd.DataFrame,dict[str, float]]:

    from tm_solarshift.models import (trnsys, postprocessing)
    DEWH: GasHeaterStorage = sim.DEWH
    kgCO2_TO_kgCH4 = 44. / 16. #Assuming pure methane for gas
    heat_value = DEWH.heat_value.get_value("MJ/kg_gas")
    eta = sim.DEWH.eta.get_value("-")

    trnsys_dewh = trnsys.TrnsysDEWH(DEWH=DEWH, ts=ts)
    df_tm = trnsys_dewh.run_simulation(ts, verbose=verbose)
    out_overall = postprocessing.annual_postproc(sim, ts, df_tm)
    sp_emissions = (kgCO2_TO_kgCH4 / (heat_value * CF("MJ", "kWh")) / eta ) #[kg_CO2/kWh_thermal]

    emissions_total = out_overall["heater_heat_acum"] * sp_emissions * CF("kg", "ton")    #[tonCO2_annual]
    emissions_marginal = emissions_total
    
    out_overall["emissions_total"] = emissions_total
    out_overall["emissions_marginal"] = emissions_marginal
    out_overall["solar_ratio"] = 0.0

    return (df_tm, out_overall)