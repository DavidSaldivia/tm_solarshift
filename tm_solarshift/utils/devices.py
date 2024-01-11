from tm_solarshift.utils.general import Variable

#List of heater devices
class GasHeaterInstantaneous():
    def __init__(self):
        # Default data from:
        # https://www.rheem.com.au/rheem/products/Residential/Gas-Continuous-Flow/Continuous-Flow-%2812---27L%29/Rheem-12L-Gas-Continuous-Flow-Water-Heater-%3A-50%C2%B0C-preset/p/876812PF#collapse-1-2-1
        # Data from model Rheim 20
        self.nom_power = Variable(157., "MJ/hr")
        self.flow_water = Variable(20., "L/min")
        self.deltaT_rise = Variable(25., "dgrC")
        self.heat_value = Variable(47.,"MJ/kg_gas")
        
        #Liquid properties (water)
        self.cp = Variable(4.18,"kJ/kg-K")
        self.rho = Variable(1.,"kg/L")
