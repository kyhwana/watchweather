#!/usr/bin/env python3

# Manage a list of stations which are periodically reporting
# measured quantities such as temperature and humidity.

import datetime
import os
import json

# A dictionary of dictionaries with various quantities we can report.
# The key in stations is station name.
# Dicts should include 'time' (datetime of last update).
# For example, station['office'] -> { 'temperature': 73, 'time': <datetime> }
# Values may be numbers or strings, but will normally be strings
# because that's what's sent in web requests.
stations = {}

# The order in which to show fields.
# Read from ~/.config/watchweather/fields.
field_order = None

# How long to keep stations if they stop reporting:
expire_after = datetime.timedelta(minutes=5)

# If the environment variable WEATHER_DATA_DIR is set,
# data will be saved to JSONL files in that directory.
# Why not CSV? Because a station might report completely different
# quantities each time: there's no way to predict what columns
# would eventually be needed in a CSV file.
savedir = os.getenv("WEATHER_DATA_DIR")
if savedir and not os.path.exists(savedir):
    os.mkdir(savedir)

def initialize(expiration=None):
    '''Initialize the station list.
       The optional expiration argument is a datetime.timedelta
       specifying how long to keep stations that stop reporting.
    '''
    if expiration:
        expire_after = expiration

    # To get a list of bogus stations for testing, uncomment the next line:
    # populate_bogostations(5)

def populate_bogostations(nstations):
    '''Create a specified number of  bogus stations to test the web server.
       If you want to test layout, you probably want to create at least 5.
    '''
    import random

    stationnames = [ 'office', 'patio', 'garden', 'garage', 'kitchen',
                     'bedroom', 'roof', 'living room', 'Death Valley',
                     'Antarctica' ]
    nstations = min(nstations, len(stationnames))
    for st in stationnames[:nstations]:
        stations[st] = { 'temperature': "%.1f" % (random.randint(65, 102)),
                         'humidity':    "%.1f" % (random.randint(1, 100) / 100),
                         'time' :       datetime.datetime.now()
                       }

# The idiot python json module can't handle datetimes,
# so those have to be treated specially:
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def update_station(station_name, station_data):
    '''Update a station, adding it if it's new.
       station_data is a dictionary.
       Also prune the list of stations.
    '''
    stations[station_name] = station_data

    if savedir:
        datafilename = os.path.join(savedir, station_name) + ".jsonl"
        with open(datafilename, "a") as datafile:
            datafile.write(json.dumps(station_data, default=json_serial))
            datafile.write('\n')

    prune_stations()

def prune_stations():
    '''Remove any station that hasn't reported in a while.
    '''
    now = datetime.datetime.now()
    deleted_stations = []
    for stname in stations:
        try:
            if now - stations[stname]['time'] > expire_after:
                deleted_stations.append(stname)
        except KeyError:
            print("No 'time' in station", stname)
            pass

    for d in deleted_stations:
        del stations[d]

def station_details(stationname):
    '''Show details for just one station'''
    if not field_order:
        # XXX temporarily hardwired
        read_field_order_file(os.path.expanduser("~/.config/watchweather/fields"))

    html_out = '<table>'
    extra_fields = ''
    # st = stations[stationname]
    if stationname == 'all':
        nstations = len(stations)
        showstations = stations
        html_out += '<tr><td>'
        for stname in showstations:
            html_out += '<th>%s' % (stname)
    else:
        nstations = 1
        showstations = { stationname: stations[stationname] }

    # First collect the fields specified in field_order.
    for field in field_order:
        if not field:
            html_out += '<tr><td colspan=%d>&nbsp;' % (nstations+1)
            continue

        html_out += '<tr>\n'
        html_out += '<td>%s\n' % (field.replace('_', ' ').title())
        for stname in showstations:
            st = showstations[stname]

            # Not all stations have all fields, so be prepared
            # for a KeyError:
            try:
                html_out += '<td>%s' % st[field]
            except KeyError:
                html_out += '<td>&nbsp;'

    html_out += '</table>'
    return html_out

def stations_as_html():
    '''Return an HTML string representing all the reporting stations.
    '''
    outstr = ''
    for stname in stations:
        st = stations[stname]

        outstr += '''
<fieldset class="stationbox">

<legend>%s</legend>

<table class="datatable">
<tr>
''' % (stname)

        keys = list(st.keys())

        # Keep the keys always in the same order.
        # Generally we want temperature first, so as a TEMPORARY measure,
        # use reverse sort. XXX Be smarter about order.
        keys.sort(reverse=True)

        for key in keys:
            if key == 'time':
                continue
            outstr += '  <td>%s\n' % key
        outstr += '<tr class="bigdata">'

        for key in keys:
            if key == 'time':
                continue

            # The value got here through http and is already a string.
            # However, if it's a floating point, chances are it has
            # way too many decimal places. To avoid depending on all
            # modules to do that properly, guard against it here.
            try:
                f = float(st[key])
                st[key] = '%.1f' % f
            except:
                pass

            outstr += '  <td>%s\n' % st[key]

        if 'time' in st:
            outstr += '<tr><td colspan=10>'
            if hasattr(st['time'], 'strftime'):
                outstr += "Last updated: " + st['time'].strftime('%H:%M')
            else:
                outstr += "Last updated: " + st['time']

        outstr += '</table>\n'
        outstr += '\n</fieldset>\n'

    return outstr

def read_field_order_file(filename):
    global field_order

    try:
        fp = open(filename)
    except:
        return

    if not field_order:
        field_order = []

    for line in fp:
        line = line.strip()
        if line.startswith('#'):
            continue
        field_order.append(line)

    fp.close()

if __name__ == '__main__':
    initialize()
    print(stations_as_html())

