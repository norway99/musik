import sys
sys.path.append('../utils')
import utils

class Tissue:
    """
    A class representing a tissue in the body.

    Attributes:
    -----------
    name : str
        The name of the tissue (e.g. blood, myocardium, bone, etc.)
    c : float
        The speed of sound in the tissue (in m/s)
    rho : float
        The density of the tissue (in kg/m^3)
    sigma : float
        The standard deviation of speed of sound in the tissue (in m/s)
    wavelength : float
        The wavelength of the max-scattering-sound in the tissue (in m)
    label : int
        A label for the tissue (an integer between 0 and n)

    Methods:
    --------
    save(path: str) -> dict:
        Saves the tissue attributes to a dictionary and returns it.
    load(path: str) -> None:
        Loads the tissue attributes from a JSON file.
    """

    def __init__(self, 
                 name=None, 
                 c=1540, 
                 rho=1000,
                 sigma=1, 
                 scale=0.1, 
                 label=None):

        self.name = name
        self.c = c
        self.rho = rho
        self.sigma = sigma
        self.scale = scale
        self.label = label
	
    def save(self,):
        # utils.dict_to_json(self.__dict__)
        return self.__dict__
	
    # def load(self, filepath):
        # dictionary = utils.json_to_dict(filepath)
    def load(self, dictionary):
        self.name = dictionary['name']
        self.c = dictionary['c']
        self.rho = dictionary['rho']
        self.sigma = dictionary['sigma']
        self.scale = dictionary['scale']
        self.label = dictionary['label']
        return self
        