#90% of the time the model experiences an error of less than 10%
#83% of the time the model experiences an error of less than 5% 
#historical data deaths analysis: 02/05/2020 - 11/30/2020
import requests
from csv import reader
import plotly.graph_objects as go

api = requests.get('https://api.covidtracking.com/v1/us/daily.json')
#print(api.status_code)
alldata = api.json()

# Store accumulation of historical deaths to compare with the predictions of the model
deaths_cum = []
xDate = []

#Grab Historical Data for Deaths 
for i in range(len(alldata)-24, 96, -1): #24->02/05, 96->11/30
    dates = str(alldata[i]['date'])
    # deaths = int(str(alldata[i]['deathIncrease']))
    death = (alldata[i]['death'])
    d = 0
    # Check if Null/None - handle type conversion before appending
    if str(death) == "None":
        d = 0
    else:
        d = int(str(death))
    # Append to deaths_cum array
    deaths_cum.append(d)
    dates = dates[0:4] + '-' + dates[4:6] + '-' + dates[6:8]
    xDate.append(dates)
    # print(dates)

#Reach csv and save values 
modeldeaths = []
with open("us_simulation.csv", "r") as read_obj:
    # Create file pointer object to read csv file
    csv_reader = reader(read_obj)
    # Step file pointer once to omit header row
    header = next(csv_reader)
    # Last date for historic analysis
    stop_date = "2020-12-01"
    idx = 0
    # Iterate through rows of csv file line by line
    for row in csv_reader:
        # Stop when last date has been reached
        if(row[0] == stop_date):
            break
        # Create cumulative sum of daily deaths predicted by model
        # for comparison with historic data
        if idx == 0:
            modeldeaths.append(float(row[3]))
        else:
            modeldeaths.append(float(row[3]) + modeldeaths[idx-1])
        idx += 1
    
#Accuracy code
count = 0
# Iterate through cumulative deaths predicted by model
for i in range(len(modeldeaths)):
    if deaths_cum[i] == 0:
        count += 1
    else:
        # Ensure that predicted values from the model differ by less than 10% from the historic data
        if (modeldeaths[i] >= deaths_cum[i] and modeldeaths[i] / deaths_cum[i] < 1.11) or (modeldeaths[i] < deaths_cum[i] and modeldeaths[i] / deaths_cum[i] > .89):
            count += 1

# Output percent of predictions that are accurate - less than 10% (or 5%) different than historic data
print("Accuracy of predictions with 10% boundary:", count / len(modeldeaths) * 100)


#Plot Deaths
fig = go.Figure()
#plot model:
fig.add_trace(go.Scatter(x=xDate, y=modeldeaths,line_color='rgba(0,0,255,1)', name="Modeled Cumulative Deaths", line_shape='linear'))
#plot historic data:
fig.add_trace(go.Scatter(x=xDate, y=deaths_cum,line_color='rgba(255,0,0,1)',name="Historical Cumulative Deaths", line=dict(dash='dash'),  line_shape='linear'))

fig.update_layout(title='Modled vs. Actual Deaths in the US', xaxis_title='Date', yaxis_title='Population')
fig.show()
fig.write_html("ProjectedDeaths.html")

