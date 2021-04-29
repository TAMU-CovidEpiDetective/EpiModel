# Where the model is ran for simulation
# Mathmatical computations done HERE
# Will return model outputs

import datetime
import numpy as np 
from input_settings import *

# Will return # of new daily cases on day i out of N days
def get_daily_imports(model_build, i):
	N = model_build.N
	assert i < N, 'day index must be less than total days'

	if hasattr(model_build, 'beginning_days_flat'):
		beginning_days_flat = model_build.beginning_days_flat
	else:
		beginning_days_flat = 10
	assert beginning_days_flat >= 0

	if hasattr(model_build, 'end_days_offset'):
		end_days_offset = model_build.end_days_offset
	else:
		end_days_offset = int(N - min(N, DAYS_WITH_IMPORTS))
	assert beginning_days_flat + end_days_offset <= N
	n_ = N - beginning_days_flat - end_days_offset + 1

	daily_imports = model_build.daily_imports * \
		(1 - min(1, max(0, (i-beginning_days_flat+1)) / n_))

	if model_build.country_str not in ['China', 'South Korea', 'Australia'] and not \
			hasattr(model_build, 'end_days_offset'):
		# we want to maintain ~10 min daily imports a day
		daily_imports = max(daily_imports, min(10, 0.1 * model_build.daily_imports))

	return daily_imports

# Will run the SEIR simulation when given the ModelBuild object
def run(model_build):
	dates = np.array([model_build.first_date + datetime.timedelta(days=i) \
        for i in range(model_build.N)])
	infections = np.array([0.] * model_build.N)
	hospitalizations = np.zeros(model_build.N) * np.nan
	deaths = np.array([0.] * model_build.N)
	reported_deaths = np.array([0.] * model_build.N)
	mortaility_rates = np.array([model_build.MORTALITY_RATE] * model_build.N)

	assert infections.dtype == hospitalizations.dtype == \
		deaths.dtype == reported_deaths.dtype == mortaility_rates.dtype == np.float64

	#find the nomalized deaths/infections versions of probability distribution
	#later invert the norms for simplifying the convolution
	#begining of array are the farthest days out
	deaths_norm = DEATHS_DAYS_ARR[::-1] / DEATHS_DAYS_ARR.sum()
	infections_norm = INFECTIOUS_DAYS_ARR[::-1] / INFECTIOUS_DAYS_ARR.sum()
	# now reduce infections in farther part of period based on reduction_idx
	if hasattr(model_build, 'quarantine_fraction'):
		infections_norm[:model_build.reduction_idx] = \
			infections_norm[:model_build.reduction_idx] * (1 - model_build.quarantine_fraction)
		infections_norm[model_build.reduction_idx] = \
			(infections_norm[model_build.reduction_idx] * 0.5) + \
			(infections_norm[model_build.reduction_idx] * 0.5 * \
				(1 - model_build.quarantine_fraction))

	# higher immunity mult, higher effect of immunity
	assert 0 <= model_build.immunity_mult <= 2, model_build.immunity_mult

	# Compute Infections ------------------------------------------------------------>
	effective_r_arr = []
	for i in range(model_build.N):
		if i < INCUBATION_DAYS+len(infections_norm):
			# initialize infections
			infections[i] = model_build.daily_imports
			effective_r_arr.append(model_build.R_0_ARR[i])
			continue

		# assume 50% of population lose immunity after 6 months
		infected_so_far = infections[:max(0, i-180)].sum() * 0.5 + infections[max(0, i-180):i-1].sum()
		perc_population_infected_so_far = \
			min(1., infected_so_far / model_build.population)
		assert 0 <= perc_population_infected_so_far <= 1, perc_population_infected_so_far

		r_immunity_perc = (1. - perc_population_infected_so_far)**model_build.immunity_mult
		effective_r = model_build.R_0_ARR[i] * r_immunity_perc

		# Now apply a convolution on the infections norm array
		s = (infections[i-INCUBATION_DAYS-len(infections_norm)+1:i-INCUBATION_DAYS+1] * \
			infections_norm).sum() * effective_r
		infections[i] = s + get_daily_imports(model_build, i)
		effective_r_arr.append(effective_r)

	model_build.perc_population_infected_final = perc_population_infected_so_far #??????????????
	assert len(model_build.R_0_ARR) == len(effective_r_arr) == model_build.N
	model_build.effective_r_arr = effective_r_arr

	# Compute Hospitalizations ------------------------------------------------------------>
	# Estimates hospitalizations with sum of window of n days of (new infections * hospitalization rate)
	# this is hosp beds in use on day _i, not new hospitalizations
	if model_build.compute_hospitalizations:
		for _i in range(model_build.N):
			start_idx = max(0, _i-DAYS_UNTIL_HOSPITALIZATION-DAYS_IN_HOSPITAL)
			end_idx = max(0, _i-DAYS_UNTIL_HOSPITALIZATION)
			hospitalizations[_i] = int(HOSPITALIZATION_RATE * infections[start_idx:end_idx].sum())

	# Compute True Deaths ------------------------------------------------------------>
	assert len(deaths_norm) % 2 == 1, 'deaths arr must be odd length'
	deaths_offset = len(deaths_norm) // 2
	#next, do convolution on deaths norm array
	for _i in range(-deaths_offset, model_build.N-DAYS_BEFORE_DEATH):
		infections_subject_to_death = (infections[max(0, _i-deaths_offset):_i+deaths_offset+1] * \
			deaths_norm[:min(len(deaths_norm), deaths_offset+_i+1)]).sum()
		true_deaths = infections_subject_to_death * model_build.ifr_array[_i + DAYS_BEFORE_DEATH]
		deaths[_i + DAYS_BEFORE_DEATH] = true_deaths

	# Compute Reported Deaths ------------------------------------------------------------>
	death_reporting_lag_arr_norm = model_build.get_reporting_delay_distribution()
	assert abs(death_reporting_lag_arr_norm.sum() - 1) < 1e-9, death_reporting_lag_arr_norm
	# now converting true deaths to reported deaths
	# remove pool of undetected deaths, apply reporting delay that will dec over time
	for i in range(model_build.N):
		detected_deaths = deaths[i] * (1 - model_build.undetected_deaths_ratio_array[i])
		max_idx = min(len(death_reporting_lag_arr_norm), len(deaths) - i)
		reported_deaths[i:i+max_idx] += \
			(death_reporting_lag_arr_norm * detected_deaths)[:max_idx]

	return dates, infections, hospitalizations, reported_deaths