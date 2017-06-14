
# coding: utf-8

# In[1]:

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from datetime import datetime, timedelta
import os

get_ipython().magic('matplotlib notebook')


# In[2]:

import pprint
pp = pprint.PrettyPrinter(indent=4)


# In[3]:

from bs4 import BeautifulSoup


# In[4]:

### Main Processsing Code


main_origins = set()
main_destinations = set()


df = pd.DataFrame()

# directory = 'outbound'
# earliest_departure = datetime.strptime('16JUN 2017 10:01AM', '%d%b %Y %I:%M%p')
# latest_arrival = datetime.strptime('17JUN 2017 9:00AM', '%d%b %Y %I:%M%p')

directory = 'return'
earliest_departure = datetime.strptime('18JUN 2017 2:00PM', '%d%b %Y %I:%M%p')
latest_arrival = datetime.strptime('19JUN 2017 6:00PM', '%d%b %Y %I:%M%p')

## Loop over HTML files, convert to DataFrame
for fn in os.listdir(directory):
    if fn[-5:] == '.html':
        print(fn)
        
        fullpath = os.path.join(directory, fn)
        
        df = df.append(pd.read_html(fullpath, attrs={'id': 'flightsOut'})[0], ignore_index=True)
        
        # Get Origin / Destination from HTML
        with open(fullpath, 'rb') as html:
            soup = BeautifulSoup(html, 'lxml')

            origin = soup.find(id="fromAirport").get_attribute_list('value')[0]
            destination = soup.find(id="toAirport").get_attribute_list('value')[0]
            
            
            main_origins.add(origin)
            main_destinations.add(destination)

print('Origins:', main_origins)
print('Destinations:', main_destinations)


## Parse Raw DataFrame
parsed_df = df[['From', 'To', 'Aircraft']].copy()


k = 0
for n, row in df.iterrows():
    
    # Group flights by route
    if row['From'] in main_origins:
        k += 1
    
    parsed_df.loc[n, 'Group'] = k
#     parsed_df.loc[n, 'flight_num'] = row['Flight'].split()[0]
    parsed_df.loc[n, 'flight_num'] = int(''.join(c for c in str(row['Flight']) if c.isdigit()))
    
    
    # Combine departure date/time
    datetime_object = datetime.strptime('{} 2017 {}'.format(row['Departure Date'], row['Departure Time']), '%d%b %Y %I:%M%p')
    parsed_df.loc[n, 'dep_datetime'] = datetime_object
    
    # Combine Arrival date/time
    datetime_object = datetime.strptime('{} 2017 {}'.format(row['Arrival Date'], row['Arrival Time']), '%d%b %Y %I:%M%p')
    parsed_df.loc[n, 'arr_datetime'] = datetime_object
    
    # Combine total available seats
    total_seats = {'av': 0, 'au':0, 'cap':0}
    
    for label, col in zip(['business', 'first', 'main'], ['BusinessAv/Au(Cap)', 'First ClassAv/Au(Cap)', 'Main CabinAv/Au(Cap)']):
        av, temp = row[col].split('/')
        au, temp2 = temp.split('(')
        cap = temp2.replace(')', '')
        
        seats = {'av': int(av), 'au':int(au), 'cap':int(cap)}
        
        for key in ['av', 'au', 'cap']:
            total_seats[key] = total_seats[key] + seats[key]
            
    for key in ['av', 'au', 'cap']:
        parsed_df.loc[n, 'total_{}'.format(key)] = total_seats[key]


## Remove routes with more than one layover
single_stop_df = pd.DataFrame()

for n, group in parsed_df.groupby('Group'):
    if group.shape[0] <= 2:
        single_stop_df = single_stop_df.append(group)
        
parsed_df = single_stop_df


## Create set of layover options
origins = set({})
destinations = set({})
layovers = set([])

for r, row in parsed_df.iterrows():
    origins.add(row.From)
    destinations.add(row.To)
    
    if row.From in main_origins:
        layovers.add(row.To)
    
    if row.To in main_destinations:
        layovers.add(row.From)
        
print(origins, destinations, layovers)


## Reduce dataframe to only unique flights
dedup_df = parsed_df.drop_duplicates('flight_num')


dedup_df = dedup_df[dedup_df.dep_datetime >= earliest_departure]
dedup_df = dedup_df[dedup_df.arr_datetime <= latest_arrival]


# In[26]:

def find_first_last(all_flights, selected_origins, selected_layovers, selected_destinations):
    first_flights = pd.DataFrame()

    for n, flight in all_flights.iterrows():
        if flight.From in selected_origins and flight.To in selected_layovers:
            first_flights = first_flights.append(flight, ignore_index=True)

    if first_flights.shape[0] > 0:
        first_flights = first_flights.sort_values('dep_datetime')

    last_flights = pd.DataFrame()

    for n, flight in all_flights.iterrows():
        if flight.From in selected_layovers and flight.To in selected_destinations:
            last_flights = last_flights.append(flight, ignore_index=True)

    if last_flights.shape[0] > 0:
        last_flights = last_flights.sort_values('arr_datetime')
    
    return first_flights, last_flights

def plot_flight(flight, line_count, ax, c='c'):
    
    plt.plot([flight.dep_datetime, flight.arr_datetime], [line_count, line_count], '-', c=c, linewidth=flight.total_av/2, solid_capstyle='butt')
    
    dep_str = '{} {}'.format(flight.dep_datetime.strftime('%I:%M%p'), flight.From)
    arr_str = '{} {}'.format(flight.To, flight.arr_datetime.strftime('%I:%M%p'))
    
    t = ax.text(flight.dep_datetime, line_count, dep_str+'->'+arr_str, ha="left", va="bottom")
#     t = ax.text(flight.arr_datetime, line_count, arr_str, ha="center", va="bottom")
    
    desc_str = 'FN: {}, Av: {}'.format(flight.flight_num, flight.total_av)
    t = ax.text(flight.arr_datetime, line_count, desc_str, ha="right", va="top")


# In[27]:

def plot_origin(all_flights, first_flights, fig=None):
    ### Origin Flights first
    if fig is None:
        fig = plt.figure()
    else:
        print('clearing')
        fig.clf()

    ax = plt.gca()

    myFmt = mdates.DateFormatter('%m-%d %I:%M%p')
    ax.xaxis.set_major_formatter(myFmt)
    labels = ax.get_xticklabels()
    plt.setp(labels, rotation=30, fontsize=8)



    line_count = 1
    for n, flight in first_flights.iterrows():

        plot_flight(flight, line_count, ax)
        line_count += 1

        connections = all_flights[all_flights.From == flight.To]
        connections = connections[connections.dep_datetime >= flight.arr_datetime + timedelta(minutes=25)].sort_values('dep_datetime')

        for n, conn_flight in connections.iterrows():

            plot_flight(conn_flight, line_count, ax, c='y')

            line_count += 1

    fig.set_size_inches(13, line_count*0.4)

    plt.grid()

    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    ax2.xaxis.set_major_formatter(myFmt)
    ax2.xaxis.set_ticks(ax.get_xticks())
    labels = ax2.get_xticklabels()
    plt.setp(labels, rotation=30, fontsize=8)

    plt.tight_layout()

    plt.ylim([line_count,0])
    
def plot_destination(all_flights, last_flights, fig=None):
    ### Destination Flights first
   
    if fig is None:
        fig = plt.figure()
    else:
        print('clearing')
        fig.clf()

    ax = plt.gca()

    myFmt = mdates.DateFormatter('%m-%d %I:%M%p')
    ax.xaxis.set_major_formatter(myFmt)
    labels = ax.get_xticklabels()
    plt.setp(labels, rotation=30, fontsize=12)

    line_count = 1
    k=0

    for n, flight in last_flights.iterrows():


            connections = all_flights[all_flights.To == flight.From]

            connections = connections[connections.arr_datetime <= flight.dep_datetime - timedelta(minutes=25)].sort_values('dep_datetime')

            for n, conn_flight in connections.iterrows():

                plot_flight(conn_flight, line_count, ax, c='c')

                line_count += 1

            if connections.shape[0] > 0:

                plot_flight(flight, line_count, ax, c='y')
                line_count += 1

    fig.set_size_inches(13, line_count*0.4)
    plt.grid()
    
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    ax2.xaxis.set_major_formatter(myFmt)
    ax2.xaxis.set_ticks(ax.get_xticks())
    labels = ax2.get_xticklabels()
    plt.setp(labels, rotation=30, fontsize=8)
    
    plt.tight_layout()

    plt.ylim([line_count,0])


# In[28]:

def make_date_sliders(start,end,freq='D',fmt='%Y-%m-%d', disp_fmt='%Y-%m-%d'):
        """
        Parameters
        ----------
        start : string or datetime-like
            Left bound of the period
        end : string or datetime-like
            Left bound of the period
        freq : string or pandas.DateOffset, default='D'
            Frequency strings can have multiples, e.g. '5H' 
        fmt : string, defauly = '%Y-%m-%d'
            Format to use to display the selected period

        """
        date_range=pd.date_range(start=start,end=end,freq=freq)
        
        options = [(item.strftime(disp_fmt),item) for item in date_range]
        
        slider_start = widgets.SelectionSlider(
            description='start',
            options=options,
            continuous_update=False
        )
        
        slider_end = widgets.SelectionSlider(
            description='end',
            options=options,
            continuous_update=False,
            value=options[-1][1]
        )
        return slider_start, slider_end


# In[30]:

import ipywidgets as widgets

origin_select = widgets.SelectMultiple(
    options=list(main_origins),
    value=list(main_origins),
    description='Origins:',
    disabled=False,
)

destination_select = widgets.SelectMultiple(
    options=list(main_destinations),
    value=list(main_destinations),
    description='Destinations:',
    disabled=False,
)

layover_select = widgets.SelectMultiple(
    options=list(layovers),
    value=list(layovers),
    description='Layovers:',
    disabled=False,
)

plot_radio = widgets.RadioButtons(
    options=['Origin First', 'Destination First'],
    value='Origin First',
    description='Plot Order:',
    disabled=False
)

## Date sliders
fmt='%Y-%m-%d %I:%M%p'

start_date = datetime.strftime(dedup_df.dep_datetime.min(), fmt)
end_date = datetime.strftime(dedup_df.arr_datetime.max(), fmt)

slider_start, slider_end = make_date_sliders(start=start_date, end=end_date, freq='H',fmt=fmt, disp_fmt='%m-%d %I:%M%p')


fig = plt.figure()

def change_states(change):
    
    # pp.pprint(change)
    if change['name'] == 'value':
        
        selected_origins = origin_select.value
        selected_layovers = layover_select.value
        selected_destinations = destination_select.value
        
        all_flights = dedup_df[dedup_df.dep_datetime > slider_start.value]
        all_flights = all_flights[all_flights.arr_datetime < slider_end.value]
                
        first_flights, last_flights = find_first_last(all_flights, selected_origins, selected_layovers, selected_destinations)
        
        if plot_radio.value == 'Origin First':
            if first_flights.shape[0] > 0:
                plot_origin(all_flights, first_flights, fig=fig)
            else:
                fig.clf()
        else:
            if last_flights.shape[0] > 0:
                plot_destination(all_flights, last_flights, fig=fig)
            else:
                fig.clf()


origin_select.observe(change_states)
layover_select.observe(change_states)
destination_select.observe(change_states)
plot_radio.observe(change_states)
slider_start.observe(change_states)
slider_end.observe(change_states)

change_states({'name': 'value'})


items = [plot_radio, origin_select, layover_select, destination_select]
widgets.VBox([widgets.HBox([slider_start, slider_end]), widgets.HBox(items)])



# In[42]:




# In[ ]:



