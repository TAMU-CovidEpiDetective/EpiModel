#Script to run the intake of "--" Prameters
#ex) python entry_point.py -v --best_settings_dir best_settings/latest --country US  --sim_end_date 2021-03-29 --save_csv_filename us_simulation.csv

import argparse #parse the args
import datetime
import glob
import json #file formatting, Best Params is JSON files
import os #help look for files
import numpy as np 

from model_build import ModelBuild # importing object made
from model_run import run 
from helper import str_to_date, remove_space_region

def load_best_settings_from_file(best_settings_dir, country, region=None, subregion=None):
	# will return direct with the input settngs for specifc region
	# ex) country=US, region=None, subregion=None -> US
	# ex) country=US, region=CA, subregion=Los Angeles -> Los Angeles County, California, US
	# best_settings_dir is the directory for where best_settings is

	# Checks on path for existing file T/F
	assert os.path.isdir(best_settings_dir), f'best_settings directory doesnt exist: {best_settings_dir}'
	# check parameter exists
	assert country, 'Specify country to upload settings from file (region/subregion optional)'

	#removing space from inputs and rename to 'XX_', string formating
	country_ = remove_space_region(country)
	region_ = remove_space_region(region)
	subregion_ = remove_space_region(subregion)

	
	# inputs check
	if subregion_: # must specifiy subregion
		if country_ == 'US': #specified US as country
			assert region_, 'say state for US subregion' #pause to get subregion input if not there
			best_settings_fname_search = f'{best_settings_dir}/subregion/*{country_}_{region_}_{subregion_}.json' #assmble string for, "/" folders, into variable
		else:
			best_settings_fname_search = f'{best_settings_dir}/subregion/*{country_}_{subregion_}.json' #assemble string for no region
	elif country_ != 'US':
		assert region_ == 'ALL', f'region not supported for non-US countries: {region_}' #same as above w/o US
		best_settings_fname_search = f'{best_settings_dir}/global/*{country_}_ALL.json'
	else:
		if region_:
			best_settings_fname_search = f'{best_settings_dir}/*US_{region_}.json'
		else:
			best_settings_fname_search = f'{best_settings_dir}/*US_ALL.json'
	best_settings_fnames = glob.glob(best_settings_fname_search) #glob find all pathnames for string we made, find best match. returns array of matched files

	assert len(best_settings_fnames) > 0, f'File not found: {best_settings_fname_search}' #checking match from glob.glob
	assert len(best_settings_fnames) == 1, f'Multiple files: {best_settings_fnames}' #check only one match found
	best_settings_fname = best_settings_fnames[0] #pulls first index of outputa array from glob

	print(f'loading settings file: {best_settings_fname}') #update user on what is going on
	with open(best_settings_fname) as f: #opening file
		best_settings = json.load(f) #using json library, saying it is in .json format

	return best_settings #returned nicely formated json file data


def convert_mean_settings_to_settings_dict(mean_settings):
	# converts list [setting_name, setting_value_raw] pairs to dictionary setting_name to setting_value
	# putting format into variable names 
	# string dates into datetime objects for subtracting in python
	settings_dict = {} #initialize dictionary
	for setting_name, setting_value_raw in mean_settings: #iterate through every key and value in mean settings list 
		try: #error handling
			settings_dict[setting_name] = str_to_date(setting_value_raw) #type casting to date
		except (TypeError, ValueError): #if error, accept error then handle by keeping value
			settings_dict[setting_name] = setting_value_raw
	
	return settings_dict #return params dictionary now, instead of list


def convert_str_value_to_correct_type(setting_value, old_value, use_timedelta=False): # to check data type of old value and match it 
	# convert setting value to same type as old_value 
	# essentially helper fxn for data types, typecasting
	for primitive_type in [bool, int, float]: #valid data type list
		if isinstance(old_value, primitive_type): #if old value matched to one in prmitive type list, type cast it as that type
			return primitive_type(setting_value)

	if isinstance(old_value, datetime.date): #check datetime object 
		if use_timedelta: #handles case if computing difference between two times
			return datetime.timedelta(days=int(setting_value))
		return str_to_date(setting_value) # convert string to date

	raise NotImplementedError(f'unknown type for value: {type(old_value)}') #will raise error if old value wasn't in type list


def main(args): # definition of main function
	#will get values from settings if specified
    country = args.country
    region = args.region
    subregion = args.subregion
    skip_hospitalizations = args.skip_hospitalizations
    quarantine_perc = args.quarantine_perc
    quarantine_effectiveness = args.quarantine_effectiveness
    verbose = args.verbose	

    if country != 'US' and not region: #if not us, default to ALL region aka all country
    	region = 'ALL'

    best_settings_type = args.best_settings_type #specifying argument 
    assert best_settings_type in ['mean', 'median', 'top', 'top10'], best_settings_type #default to mean, but can change to other inputs listed only

    if args.best_settings_dir: #loading settings from file
    	best_settings = load_best_settings_from_file(args.best_settings_dir, country, region, subregion)
    	sim_start_date  = str_to_date(best_settings['first_date']) #file create date #inside best settings object, acessing keys, and getting value to convert to date
    	sim_create_date = str_to_date(best_settings['date']) 
    	sim_end_date = str_to_date(best_settings['projection_end_date'])

    	region_settings = {'population': best_settings['population']} #dictionary region settings, using key-(population) to get value
    	settings_type_name = f'{best_settings_type}_settings' #default to mean params
    	if verbose: #checking if verbose specified, used to print the information of sim
    		print('best settings type', best_settings_type)
    	settings_dict = convert_mean_settings_to_settings_dict(best_settings[settings_type_name]) #key-(setting type name), within json file, calling for dictionary conversion from list format
    else:
    	# hard code of settings if not using best settings files
    	sim_start_date = datetime.date(2020,2,1)
    	sim_create_date = datetime.date.today()
    	sim_end_date = datetime.date(2020,10,1)

    	region_settings = {'population': 332000000}
    	settings_dict = {
    		'INITIAL_R_0' : 2.24,
    		'LOCKDOWN_R_0' : 0.9,
            'INFLECTION_DAY' : datetime.date(2020,3,18),
            'RATE_OF_INFLECTION' : 0.25,
            'LOCKDOWN_FATIGUE' : 1.,
            'DAILY_IMPORTS' : 500,
            'MORTALITY_RATE' : 0.01,
            'REOPEN_DATE' : datetime.date(2020,5,20),
            'REOPEN_SHIFT_DAYS': 0,
            'REOPEN_R' : 1.2,
            'REOPEN_INFLECTION' : 0.3,
            'POST_REOPEN_EQUILIBRIUM_R' : 1.,
            'FALL_R_MULTIPLIER' : 1.001,	
    	}

    if args.sim_start_date: #converting specified string from command line into string, if not using file data
    	sim_start_date = str_to_date(args.sim_start_date)
    if args.sim_end_date:
    	sim_end_date = str_to_date(args.sim_end_date)

    if args.set_setting: #manually over writing param values
    	print('---------------------------------------')
    	print('Overwriting settings from command line...')
    	for setting_name, setting_value in args.set_setting:
    		assert setting_name in settings_dict, f'Unrecognized setting: {setting_name}' #in file dictionary, does it exist? 
    		old_value = settings_dict[setting_name] #original value from either file or hard coded, now in dictionary
    		new_value = convert_str_value_to_correct_type(setting_value, old_value) #taking old value into fxn to check data type of old value and match it
    		print(f'Setting {setting_name} to: {new_value}') #output update
    		settings_dict[setting_name] = new_value #update in dictionary 

    if args.change_setting: #manually inc/dec to param values
        print('---------------------------------------')
        print('Changing settings from command line...')
        for setting_name, value_change in args.change_setting:
        	assert setting_name in settings_dict, f'Unrecognized setting: {setting_name}' #in file dictionary, does it exist? 
        	old_value = settings_dict[setting_name]
        	new_value =  old_value + convert_str_value_to_correct_type(value_change, old_value, use_timedelta=True) #inc or dec paramter by specified amount 
        	print(f'changing {setting_name} from {old_value} to {new_value}')
        	settings_dict[setting_name] = new_value

    #building region model object, by passing in command line object
    model_build = ModelBuild(country, region, subregion, sim_start_date, sim_create_date, sim_end_date, 
    	region_settings, compute_hospitalizations=(not skip_hospitalizations))

    if quarantine_perc > 0: #not null, was specified 
        print(f'Quarantine percentage: {quarantine_perc:.0%}') #print the specification
        print(f'Quarantine effectiveness: {quarantine_effectiveness:.0%}') #print the effectiveness 
        assert quarantine_effectiveness in [0.025, 0.1, 0.25, 0.5], \
            ('must specify --quarantine_effectiveness percentage.'
                ' Possible values: [0.025, 0.1, 0.25, 0.5]') #only these values allowed are in list
        quarantine_effectiveness_to_reduction_idx = {0.025: 0, 0.1: 1, 0.25: 2, 0.5: 3}
        model_build.quarantine_fraction = quarantine_perc #updating model
        model_build.reduction_idx = \
            quarantine_effectiveness_to_reduction_idx[quarantine_effectiveness]

    if verbose: #print if spefied verbose opttion
        print('================================')
        print(model_build)
        print('================================')
        print('Parameters:') #printing parameters 
        for setting_name, setting_value in settings_dict.items():
            print(f'{setting_name:<25s} : {setting_value}')

    # putting settings to model_build
    settings_tups = tuple(settings_dict.items()) #type casting, changing parameters into tuple form from dictionary
    #saving params in init_params
    model_build.init_settings(settings_tups) #takes all parameters into tuple form to feed into init_params in model_build

    if verbose:
        print('--------------------------')
        print('Running simulation...')
        print('--------------------------')

    #runing the sim
    dates, infections, hospitalizations, deaths = run(model_build) #calls run, returns those listed
    # N = days of sim from sim_start_date to sim_end_date, in list
    # dates = day i, rep by datetime.date
    # infections = day i, # of new infections
    # hospitalizations = day i, # of taken hosp. beds
    # deaths = day i, # of Added deaths

    # check for lengths of lists and start/end validitity 
    assert len(dates) == len(hospitalizations) == len(deaths) #should all be same lenghts
    assert dates[0] == sim_start_date #check matching dates
    assert dates[-1] == sim_end_date #check matching dates

    if verbose: #printing out info if called
        infections_total = infections.cumsum() #cumil sum of infections
        deaths_total = deaths.cumsum() #cumil sum of deaths
        for i in range(len(dates)): #loop through dates
            hospitalization_str = ''
            if not skip_hospitalizations:
                hospitalization_str = f'Hospital beds in use: {hospitalizations[i]:,.0f} - ' #printing hosp beds on day i

            daily_str = (f'{i+1:<3} - {dates[i]} - ' #one day is one iteration, making string with below values: 
				f'New / total infections: {infections[i]:,.0f} / {infections_total[i]:,.0f} - ' 
	            f'{hospitalization_str}'
	            f'New / total deaths: {deaths[i]:,.2f} / {deaths_total[i]:,.1f} - '
	            f'Mean R: {model_build.effective_r_arr[i]:.3f} - '
	            f'IFR: {model_build.ifr_array[i]:.2%}')
            print(daily_str) #print out assembled string for the day and repeat
    print('--------------------------------------------------------')
    print(f'End of simulation       : {model_build.projection_end_date}')
    print(f'Total infections        : {infections.sum():,.0f}')
    
    if not skip_hospitalizations:
        print(f'Peak hospital beds used : {hospitalizations.max():,.0f}')
    print(f'Total deaths            : {deaths.sum():,.0f}')

    # for saving data in CSV
    if args.save_csv_filename: #format data in neat comma separated format for results
    	dates_str = np.array(list(map(str, dates)))
    	combined_arr = np.vstack((dates_str, infections, hospitalizations, deaths, model_build.effective_r_arr)).T
    	headers = 'Dates, Infections, Hospitalizations, Deaths, Mean_rt'
    	np.savetxt(args.save_csv_filename, combined_arr, '%s', delimiter=',', header=headers)
    	print('------------------------------\nSaved file to:', args.save_csv_filename)

# Starts running here, entry point
# will inspect command line for arguments and do appropriate type and action known from add_argument functions, then will store into args variable
# add argument, check to see it has it, if yes store
# parser essentially, splicing and extracting what is needed
#interpreter created values name and main when run script from command line, will evaluate to true 
#parser object of type argument parser, holds info for parameters, building parser
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=('Script to run simulations using the SEIR model. Example: '
            '`python entry_point.py -v --best_settings_dir best_settings/latest --country US`'))
    parser.add_argument('--skip_hospitalizations', action='store_true',
        help=('Skip the calculation of the number of occupied hospital beds.'
            ' Note that we have a very basic hospitalization heuristic, so exercise caution if you use it.'
            ' We skip hospitalizations in our production model to improve performance.'))
    parser.add_argument('--quarantine_perc', type=float, default=0,
        help=('percentage of people we put in quarantine (e.g. 0.5 = 50%% quarantine) (default is 0).'
            ' We do not use this in production.'))
    parser.add_argument('--quarantine_effectiveness', type=float, default=-1,
        help=('if --quarantine_perc is set, this is the percent reduction in transmission after quarantine.'
            'For example, 0.5 means a 50%% reduction in transmission. Valid values: 0.025, 0.1, 0.25, 0.5.'))
    parser.add_argument('--save_csv_filename',
        help='output csv file to save data')	

    parser.add_argument('--sim_start_date',
        help=('Set the start date of the simulation.'
            'This will override any existing values (Format: YYYY-MM-DD)'))
    parser.add_argument('--sim_end_date',
        help=('Set the end date of the simulation.'
            'This will override any existing values (Format: YYYY-MM-DD)'))

    parser.add_argument('--best_settings_dir',
        help='if passed, will load parameters from file based on the country, region, subregions')
    parser.add_argument('--best_settings_type', default='mean',
        choices=['mean', 'median', 'top', 'top10'],
        help='we save four types of params for each region (default mean)')
    parser.add_argument('--set_setting', action='append', nargs=2,
        help=('Takes two inputs, the name of the parameter and its value'))
    parser.add_argument('--change_setting', action='append', nargs=2,
        help=('Takes two inputs, the name of the parameter and the amount to increase/decrease'))
    parser.add_argument('--country', 
        help='only necessary if loading params from --best_settings_dir')
    parser.add_argument('--region', default='',
        help='only necessary if loading params from --best_settings_dir')
    parser.add_argument('--subregion', default='',
        help='only necessary if loading params from --best_settings_dir')

    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()	#will use to store them into args
    							
    np.random.seed(0) #seeding random generatror fo reproducible results

    # begining outputs after execution
    print('====================================================')
    print('SEIR simulation')
    print('Start time:', datetime.datetime.now())
    print('====================================================')

    main(args) #start process from chunk of code above, this causes to start running

    print('====================================================')
    print('====================================================')
    print('ALL Done!!! - End time:', datetime.datetime.now())
    print('====================================================')
    print('====================================================')


