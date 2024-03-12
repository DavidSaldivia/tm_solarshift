import pandas as pd

FILE_RESISTIVE = "path//to//file.csv"
FILE_HP = "path//to//file.csv"
FILE_CASES = "path//to//file.csv"

TYPE_HEATERS = ["Heat Pump", ""]
LIST_LOCATIONS = ["Sydney"]

LIST_DNSP = ["Ausgrid"]

def calculate_capital_cost(heater):

    nom_power = heater.nom_power
    capital_cost = nom_power.get_value("W") * 20.

    return capital_cost


def calculate_capital_cost_ruby(water_heater_type, model):

    if water_heater_type == "Resistive":
        heaters = pd.read_excel(FILE_RESISTIVE)

        heater = heaters.loc[model]
        
        nom_cap = heater.nom_cap
        capital_cost = nom_cap * 20.

        return capital_cost

    elif water_heater_type == "HeatPump":
        heaters = pd.read_csv(FILE_HP)
        nom_cap = heater.nom_cap
        capital_cost = nom_cap * 20.
        return capital_cost

    else:
        raise ValueError("type of water heater is wrong.")


def calculate_annual_bill(case_parameters) -> float:

    #Retrieve data
    city = case_parameters["city"]

    #Do calculations
    pass

    #Return

    return None


def retrieve_data(case_id: int = 1) -> pd.DataFrame:

    cases_data = pd.read_csv(FILE_CASES, index_col=0)
    case_parameters = cases_data.loc[case_id]

    return case_parameters


def main():

    # If using tm_solarshift

#     from tm_solarshift.devices import (
#     ResistiveSingle, HeatPump, GasHeaterInstantaneous
#     )
    # heater = ResistiveSingle()
    # capital_cost = calculate_capital_cost(heater)

    # heater = ResistiveSingle.from_model_file(model="491080")
    # capital_cost = calculate_capital_cost(heater)

    # heater = HeatPump()
    Cases = [1, 2, 3, 4]
    for case_id in Cases:
        case_id = 1
    
        case_parameters = retrieve_data(case_id = case_id)
        capital_cost = calculate_capital_cost_ruby(case_parameters)
        annual_bill = calculate_annual_bill(case_parameters)

        # If working with Ruby's code
        water_heater_type = "Resistive"
        model = "000"




    # water_types = ["Resistive", "Heat Pumps"]
    # for water_type in water_types:
    #     #do something
    #     pass


    return

if __name__ == "__main__":

    main()