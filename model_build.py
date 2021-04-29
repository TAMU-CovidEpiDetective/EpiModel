# Where the model is built from settngs and specifications
# capitalized variables come from input_settings

import datetime
import numpy as np 
from input_settings import *
import helper

# machine learning fxn sigmoid, returns it from specified settings
# helps to smooth transition from low and high value to sampl
def transition_sigmoid(inflection_index, inflection_rate, low_val, high_val, check_values=True):
	if check_values: # make sure vals are correct bounds
		assert 0 < inflection_rate <=1, inflection_rate
		assert 0 < low_val <=10, low_val
		assert 0 <= high_val <=10, high_val
	shift = inflection_index
	a = inflection_rate
	b = low_val - high_val
	c = high_val
	return helper.inv_sigmoid(shift, a, b, c) #returning a function

class ModelBuild:
	# class used to recive details on settings for sim
	# used and then passed to SEIR for output infec, hosp, deaths

	def __init__(self, country_str, region_str, subregion_str, first_date, projection_create_date,
			projection_end_date, region_settings=dict(), actual_deaths_smooth=None, 
			randomize_settings=False, compute_hospitalizations=False):
		# contructor of ModelBuild Class

		# country_str = name of country
		# region_str = name of region
		# subregion_str = name of subregion
		# first_date = 1st day of sim
		# projection_create_date = date when being generated
		# region_settings = additional data like pop & hosp beds
		# actual_deaths_smooth = smoothed version of deaths
		# randomize_settings = variance training for model
		# compute_hospitalizations = compute hosp numbers, defau1t=false

		self.country_str = country_str #intializing values and storing into variables
		self.region_str = region_str
		self.subregion_str = subregion_str
		self.first_date = first_date
		self.projection_create_date = projection_create_date
		self.projection_end_date = projection_end_date
		self.region_settings = region_settings
		self.actual_deaths_smooth = actual_deaths_smooth
		self.randomize_settings = randomize_settings
		self.compute_hospitalizations = compute_hospitalizations

		self.country_holidays = None
		self.N = (self.projection_end_date - self.first_date).days + 1 #check for days

		assert self.N > DAYS_BEFORE_DEATH, 'N must be > DAYS DAYS_BEFORE_DEATH'
		if projection_create_date: #date checks validation
			assert first_date < projection_create_date, \
				 'first_date to be before projection_create_date'
			assert projection_create_date < projection_end_date, \
				 'create day before end day'


	def init_settings(self, settings_tups): #math section
		# initializes obj by saving the parameters passed in
		# also builds R/IFR vals for each days 

		assert isinstance(settings_tups, tuple), 'must be a tuple of tuples' #checking variable is tuple
		for x, y in settings_tups: #[x][y] is [name][value] elements in tuples
			if x in DATE_PARAMS: #inflection date is after 1st day
				assert y >= self.first_date, \
					f'{x} {y} must be after 1st date {self.first_date}'
			setattr(self, x, y) #setting attribute to values
		#doing same as above for reopen date
		assert self.REOPEN_DATE > self.INFLECTION_DAY, \
			f'reopen_date {self.REOPEN_DATE} has to be after inflection day {self.INFLECTION_DAY}'
		self.settings_tups = settings_tups #finalizing param wits value after checking
		# checking params in settings tups are known parameters, veriying in subset
		assert set([i[0] for i in settings_tups]).issubset(set(ALL_PARAMS)), 'unknown settings'

		# settings that arent provided
		self.place_rateof_inflection() #acessing in ModelBuild
		self.place_daily_imports()
		self.place_post_reopen_equil_r()
		self.place_fall_r_mult()

		# other values needed to run simulation
		self.immunity_mult = self.get_immunity_mult()
		self.R_0_ARR = self.build_R0_array()
		self.ifr_array = self.build_ifr_array()
		self.undetected_deaths_ratio_array = self.build_undetected_deaths_ratio_array()

	# will return the settings as a tuple with (name, value)
	def all_setting_tups(self):
		all_setting_dict = dict(self.settings_tups)
		for addl_setting in RANDOMIZED_PARAMS + POTENTIAL_RANDOMIZE_PARAMS:
			all_setting_dict[addl_setting] = getattr(self, addl_setting.lower())
		all_settings = [(x, all_setting_dict[x]) for x in ALL_PARAMS ]
		return tuple(all_settings)

	# will find r val post reopen
	def find_reopen_r(self):
		if self.LOCKDOWN_R_0 < 1 and self.country_str not in NO_LOCKDOWN_COUNTRIES:
			return max(self.LOCKDOWN_R_0, self.REOPEN_R)
		return self.REOPEN_R

	# will find & set rate of inflection for change between R0 and lockdown R0
	def place_rateof_inflection(self):
		if self.randomize_settings: #if randomize=true, generating random # between low and high values
			low, high = self.RATE_OF_INFLECTION * 0.75, self.RATE_OF_INFLECTION * 1.25
			self.rate_of_inflection = np.random.uniform(low, high)
		else: #default version
			self.rate_of_inflection = self.RATE_OF_INFLECTION

	# will calc and set daily imports to set up regions infections
	def place_daily_imports(self):
		if self.randomize_settings:
			low, high = self.DAILY_IMPORTS * 0.5, self.DAILY_IMPORTS * 1.5
			self.daily_imports = np.random.randint(low, high)
		else: #default version
			self.daily_imports = self.DAILY_IMPORTS

	# will calc and set the after reopen equilibrium R
	def place_post_reopen_equil_r(self):
	# if ModelBuild object has atrribute below and IS a number
		if hasattr(self, 'POST_REOPEN_EQUILIBRIUM_R') and \
				not np.isnan(self.POST_REOPEN_EQUILIBRIUM_R):
			post_reopen_equil_r = self.POST_REOPEN_EQUILIBRIUM_R # then, setit
			mode = None
		# Use post_reopen_equil_r (override reopen_r)
		if self.country_str in ['Egypt', 'Malaysia', 'Pakistan'] + EUROPEAN_COUNTRIES or \
				(self.country_str == 'US' and self.region_str in ['WI']):
			self.use_min_reopen_equil_r = False
		else:# Use min(reopen_r, post_reopen_equil_r)
			self.use_min_reopen_equil_r = True

		assert 0 < post_reopen_equil_r < 10, post_reopen_equil_r #checking r is 0-10 only
		self.post_reopen_equil_r = post_reopen_equil_r #setting it
		self.post_reopen_mode = mode #setting it

	# will calc and set the fall(the season) r multiplier, r increase in cold
	def place_fall_r_mult(self): #check it is a #, then update it
		if hasattr(self, 'FALL_R_MULTIPLIER') and not np.isnan(self.FALL_R_MULTIPLIER):
			fall_r_multiplier = self.FALL_R_MULTIPLIER
		self.fall_r_multiplier = fall_r_multiplier

	# will output immunity measure of region, the multiplier
	def get_immunity_mult(self):
		assert 0 <= IMMUNITY_MULTIPLIER <= 2, IMMUNITY_MULTIPLIER
		assert 0 <= IMMUNITY_MULTIPLIER_US_SUBREGION <= 2, IMMUNITY_MULTIPLIER_US_SUBREGION

		population = self.region_settings['population'] #look in dictionary for key(pop) for value
		if self.country_str == 'US':
			if self.subregion_str:
				immunity_mult = IMMUNITY_MULTIPLIER_US_SUBREGION
			else:
				immunity_mult = IMMUNITY_MULTIPLIER
		elif self.subregion_str:
			immunity_mult = IMMUNITY_MULTIPLIER
		elif population < 20000000:
			immunity_mult = IMMUNITY_MULTIPLIER
		else:
			# immunity is between IMMUNITY_MULTIPLIER and 1
			immunity_mult = transition_sigmoid( # mapping using sigmoid fxn
				50000000, 0.00000003, IMMUNITY_MULTIPLIER, 1, check_values=False)(population)

		return immunity_mult

	# will return an array of reproduction #'s' R per day
	def build_R0_array(self):
		reopen_r = self.find_reopen_r() #computes r value post reopen
		if self.use_min_reopen_equil_r: #true or false value
			post_reopen_r = min(reopen_r, self.post_reopen_equil_r) #pick min and use smallest
		else:
			post_reopen_r = self.post_reopen_equil_r
		# check lockdown fatgue is between .5 and 1.5
		assert 0.5 <= self.LOCKDOWN_FATIGUE <=1.5, self.LOCKDOWN_FATIGUE

		reopen_date_shift = self.REOPEN_DATE + \
			datetime.timedelta(days=int(self.REOPEN_SHIFT_DAYS) + DEFAULT_REOPEN_SHIFT_DAYS) #calc diff in dates with timedelta
		fatigue_idx = self.inflection_day_idx + DAYS_UNTIL_LOCKDOWN_FATIGUE
		reopen_idx = self.get_day_idx_from_date(reopen_date_shift) #finding index from date for var
		lockdown_reopen_midpoint_idx = (self.inflection_day_idx + reopen_idx) // 2

		NUMERATOR_CONST = 6
		days_until_post_reopen = int(np.rint(NUMERATOR_CONST / self.REOPEN_INFLECTION))
		assert 10 <= days_until_post_reopen <=80, days_until_post_reopen
		post_reopen_midpoint_idx = reopen_idx + days_until_post_reopen
		post_reopen_idx = reopen_idx + days_until_post_reopen *2

		if self.country_str == 'US' or (self.country_str in EUROPEAN_COUNTRIES and \
				self.post_reopen_mode and self.post_reopen_mode < 1):
			post_reopen_days_shift = 60 if (self.post_reopen_mode and self.post_reopen_mode <= 0.95) else 45 #lamda expression for post reopen days shift
		else:
			post_reopen_days_shift = 30
		fall_start_idx = self.get_day_idx_from_date(FALL_START_DATE_NORTH) - post_reopen_days_shift
		vaccine_in_effect_idx = self.get_day_idx_from_date(VACCINE_IN_EFFECT_DATE)

		# smothing transition fxn from  ex)initial R0 and Lockdown R0 to sample in between
		sig_lockdown = transition_sigmoid(self.inflection_day_idx, self.rate_of_inflection, self.INITIAL_R_0, self.LOCKDOWN_R_0)
		sig_fatigue = transition_sigmoid(fatigue_idx, 0.2, 0, self.LOCKDOWN_FATIGUE-1, check_values=False)
		sig_reopen = transition_sigmoid(reopen_idx, self.REOPEN_INFLECTION, self.LOCKDOWN_R_0 * self.LOCKDOWN_FATIGUE, reopen_r)
		sig_post_reopen = transition_sigmoid(post_reopen_idx, self.REOPEN_INFLECTION, reopen_r, post_reopen_r)

		dates = helper.date_range(self.first_date, self.projection_end_date)
		assert len(dates) == self.N #checking lengths equal

		R_0_ARR = [self.INITIAL_R_0] #building array with initial R0
		for day_idx in range(1, self.N): #N is last day index
			if day_idx < lockdown_reopen_midpoint_idx: #still in lockdown, hence fatigue
				r_t = sig_lockdown(day_idx) #setting equal to fxn at day idx 
				if abs(self.LOCKDOWN_FATIGUE - 1) > 1e-9: #checking if significant enough for update
					r_t *= 1 + sig_fatigue(day_idx) #scaling r_t based on lockdown fatigue on that day
			elif day_idx > post_reopen_midpoint_idx: #post lockdown
				r_t = sig_post_reopen(day_idx)
			else:
				r_t = sig_reopen(day_idx) #on exact day of reopen

			if day_idx > fall_start_idx: #within fall season, adjust the r value
				fall_r_mult = max(0.9, min(1.35, self.fall_r_multiplier**(day_idx - fall_start_idx))) #to the power of
				# max between .9 and what min outputs
				assert 0.9 <= fall_r_mult <= 1.5, fall_r_mult #check between .9 and 1.5
				r_t *= fall_r_mult # rt = scaled rt * fall r mult
			
			#INPUT VACCINE SECTION HERE:
			#Using X^(#of days past feb 1st)
			if day_idx > vaccine_in_effect_idx: #within time frame in which vaccine becomes effective, adjust the r value
				vaccine_r_base_rate = 1.00035 # effects will not be very great at first - vaccine requires two doses
				vaccine_r_mult = vaccine_r_base_rate**(day_idx - vaccine_in_effect_idx) # exponential increase as a majority of the populous becomes vaccinated
				r_t *= vaccine_r_mult # rt = scaled rt * vaccine r mult
			
			#check that R is stable
			if day_idx > reopen_idx and abs(r_t / R_0_ARR[-1] - 1) > 0.2: #checking rate of inc can't be > 20%
				assert False, \
					f'{str(self)} - R changed too quickly: {day_idx} {R_0_ARR[-1]} -> {r_t} {R_0_ARR}'

			R_0_ARR.append(r_t) #adding it to the array

		assert len(R_0_ARR) == self.N #check lengths = so R0 per day
		self.reopen_idx = reopen_idx #storing it to value

		return R_0_ARR #returning array of r values

	# will return an array for infection fatility rates per day
	def build_ifr_array(self):
		assert 0.9 <= MORTALITY_MULTIPLIER <= 1.1, MORTALITY_MULTIPLIER #don;t want to be too big, for exponential growth
		assert 0 < self.MORTALITY_RATE < 0.2, self.MORTALITY_RATE

		min_mortality_multiplier = MIN_MORTALITY_MULTIPLIER
		mortality_multiplier = MORTALITY_MULTIPLIER
		region_tuple_to_mortality_mult = {
			('US', 'CT') : (0.15, 0.99),
			('US', 'MA') : (0.5, mortality_multiplier),
			('US', 'ND') : (0.6, mortality_multiplier),
			('US', 'RI') : (0.4, mortality_multiplier),
		}

		if self.region_tuple[:2] in region_tuple_to_mortality_mult: #check if in tuple
			min_mortality_multiplier, mortality_multiplier = \
				region_tuple_to_mortality_mult[self.region_tuple[:2]] #first value stored in 1st, so on
		elif self.country_str in HIGH_INCOME_EUROPEAN_COUNTRIES:
			min_mortality_multiplier *= 0.75

		ifr_array = [] #creating empty array for values below
		for idx in range(self.N): #loop through all days
			#will lower ifr past 30 days becasue of improved treatments & lower age distribution
			if self.country_str in EARLY_IMPACTED_COUNTRIES: #in early impacted countries
				total_days_with_mult = max(0, idx - 30) #max between 0 and days past 30
			else:
				#other countires have a slower increasee, so use 120
				total_days_with_mult = max(0, idx - 120)

			#opposite seasons in Australiat & South Africa, use ifr mult of 1
			if self.country_str in ['Australia', 'South Africa']:
				ifr_mult = 1
			elif self.country_str in EARLY_IMPACTED_COUNTRIES: #post-reopening has a greater reduction in the IFR
				days_after_reopening = max(0, min(30, idx - (self.reopen_idx + DAYS_BEFORE_DEATH // 2))) #calc days after re-opening
				days_else = max(0, total_days_with_mult - days_after_reopening) #chosing value above 0, number of days with fixed lowering

				#don't want value to be below set min
				#calc ifr taking into account lowering after 30 days and post-reopen increase
				ifr_mult = max(min_mortality_multiplier, mortality_multiplier**days_else * MORTALITY_MULTIPLIER_US_REOPEN**days_after_reopening)

				post_reopen_days_shift = 30 if self.country_str == 'US' else 0 #shift 30 if US
				fall_start_idx = self.get_day_idx_from_date(FALL_START_DATE_NORTH) - post_reopen_days_shift
				# increase ifr begining in fall because of seasonality
				if idx > fall_start_idx: #within fall season
					ifr_mult *= 1.002**(idx - fall_start_idx) #scale current multiplier by # days into fall
			else: #not australia/suth africa or early impacted country
				ifr_mult = max(min_mortality_multiplier, mortality_multiplier**total_days_with_mult) #between min and other value

			assert 0 < min_mortality_multiplier < 1, min_mortality_multiplier #checking bounds and validitity
			assert min_mortality_multiplier <= ifr_mult <= 1, ifr_mult
			ifr = max(MIN_IFR, self.MORTALITY_RATE * ifr_mult) #between baseline and scaled mortality rate
			ifr_array.append(ifr) #add to array created

		return ifr_array #after all days return array for each day

	# will return an array of % of deaths that are undetected per day
	# values start high but decrease to 0ish over time
	def build_undetected_deaths_ratio_array(self):
		if not USE_UNDETECTED_DEATHS_RATIO: #if not supposed to use undetected deaths ration
			return list(np.zeros(self.N)) #intalize list for days with zeros

		init_undetected_deaths_ratio = 1 #initial for variable and 100%
		if self.country_str in HIGH_INCOME_COUNTRIES:
			days_until_min_undetected = 60 #timeframe lower
			min_undetected = 0.05 #scaling is lower, to reach lower% faster
		elif self.country_str in ['Ecuador', 'India', 'Pakistan', 'South Africa']:
			days_until_min_undetected = 120
			min_undetected = 0.5
		elif self.country_str in ['Bolivia', 'Indonesia', 'Peru', 'Russia', 'Belarus']:
			days_until_min_undetected = 120
			min_undetected = 0.25
		elif self.country_str in ['Brazil', 'Mexico']:
			days_until_min_undetected = 120
			min_undetected = 0.2
		else:
			days_until_min_undetected = 120
			min_undetected = 0.15

		#ex) 1-.05 / days, so calc decreasing rate of failed reported from day to day
		daily_step = (init_undetected_deaths_ratio - min_undetected) / days_until_min_undetected
		assert daily_step >= 0, daily_step #check exist > 0, so no neg

		undetected_deaths_ratio_array = []
		for idx in range(self.N): #iterate through days
			#take max between min value and  daily step with ratio
			undetected_deaths_ratio = max(min_undetected, init_undetected_deaths_ratio - daily_step * idx)
			assert 0 <= undetected_deaths_ratio <= 1, undetected_deaths_ratio #exist between 0 and 1
			undetected_deaths_ratio_array.append(undetected_deaths_ratio) #add on to array at end

		return undetected_deaths_ratio_array #will return the array

	#Will return a probability distribution of the death reporting lag per day
	def get_reporting_delay_distribution(self):
		death_reporting_lag_arr = DEATH_REPORTING_LAG_ARR #from input file
		# normalizing prob distribution, entry/sum of entry
		return death_reporting_lag_arr / death_reporting_lag_arr.sum()

	# Will get the day index for a given date
	def get_day_idx_from_date(self, date):
		return (date - self.first_date).days

	# Will get the date when given the day index
	def get_date_from_day_idx(self, day_idx):
		return self.first_date + datetime.timedelta(days=day_idx)

	#Check to see if date is in a holiday
	def is_holiday(self, date):
		if self.country_holidays is None: #if aren't set, use fxn to get dates
			self.country_holidays = helper.get_holidays(self.country_str)
		if date in self.country_holidays: #if it is in list of holidays
			return True
		if self.country_str == 'US' and date in ADDL_US_HOLIDAYS: #if it is in US, use extra list
			return True
		return False

	#Will check if country has same US seasons as the US
	def has_us_seasonality(self):
		return self.country_str not in \
			SOUTHERN_HEMISPHERE_COUNTRIES + NON_SEASONAL_COUNTRIES

	#Will check population is an integer
	@property #python using object orientated programmig, getter/setter for class
	def population(self):
		assert isinstance(self.region_settings['population'], int), 'population must be an integer'
		return self.region_settings['population'] #return value

	#Will output # of hospital beds
	@property
	def hospital_beds(self):
		return int(self.population / 1000 * self.region_settings['hospital_beds_per_1000'])

	#Will get inflection day index from date
	@property
	def inflection_day_idx(self):
		return self.get_day_idx_from_date(self.INFLECTION_DAY)

	#Will get region tuple
	@property
	def region_tuple(self):
		return (self.country_str, self.region_str, self.subregion_str)

	#Defines how object should be printed
	def __str__(self):
		return f'{self.country_str} | {self.region_str} | {self.subregion_str}' 
























