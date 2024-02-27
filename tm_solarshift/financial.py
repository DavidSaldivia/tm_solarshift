import pandas as pd



def energy_part_of_bill(
        type_tariff: str = "flat",
        tariff: float = 0.2,
        hw_elec_file: pd.DataFrame = None,
) -> float:
    
    annual_hw = pd.read_csv(hw_elec_file)
    return  tariff * annual_hw

def calculate_capital_cost():
    pass
    return

hw_elec_file = ""
#Calculate the capital cost
capital_cost = calculate_capital_cost()

#Load the tariff
tariff_type = "flat"    # [str]
tariff = 0.2            # [AUD/kWh]

#Calculate the energy part of the electricity bill
annual_bill = energy_part_of_bill("flat", tariff, hw_elec_file)

#Calculate the other charges

#Calculate other costs

#other_calculations
...
