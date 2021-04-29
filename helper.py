# Extra helper functions used throughout code
import datetime
import numpy as np 
from input_settings import DATE_STR_FMT, DASH_REGIONS ##### VERIFY SAME*********************

# Will return an inverse sigmoid fxn based on inputs
def inv_sigmoid(shift=0, a=1, b=1, c=0): # USED XYZ IN OTHER FXNIS IT OKAY
    return lambda x: b * np.exp(-(a*(x-shift))) / (1 + np.exp(-(a*(x-shift)))) + c

# Will convert a string date to a useable datetime object
def str_to_date(date_str, fmt=DATE_STR_FMT):
    return datetime.datetime.strptime(date_str, fmt).date()

# Will Return range of datetime dates between/including start date to end date
def date_range(start_date, end_date, interval=1, str_fmt=DATE_STR_FMT):
    if isinstance(start_date, str):
        start_date = datetime.datetime.strptime(start_date, str_fmt).date()
    if isinstance(end_date, str):
        end_date = datetime.datetime.strptime(end_date, str_fmt).date()
    return [start_date + datetime.timedelta(n) \
        for n in range(0, (end_date - start_date).days + 1, interval)]

# Will remove a space from region naming
def remove_space_region(region):
    return region.replace(' ', '-')

# Will add a space to region naming
def add_space_region(region):
    if region in DASH_REGIONS:
        return region
