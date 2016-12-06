#
# NDN-FCH Python Server Implementation 1.0
#
# Gregory Liu
# 

import time              # used for getting timing of requests
from flask import Flask  # server framework
from flask import request
import geoip2.database   # MaxMind GeoIP2 database support
import kdtree            # basic k-d tree library
import json              # for processing wustl geocode.json
import cPickle as pickle # for pickling geocode
import pycurl            # fetching wustl geocode
import re                # url processing

# if True, will respond to requests verbosely
verbose = False

# if True, will prompt server on startup whether or not to
# refetch WUSTL's geocode.json data object to refresh hub data
prompt_for_fetch = False

# holds geocode data
geocode = None
# MaxMind DB reader
reader = None
# K-D tree containing NamedLoc nodes of hubs
kdt = None

# DB name / location
MMDB_LOCATION = 'GeoLite2-City.mmdb'

# WUSTL Geocode URL
WUSTL_GEOCODE_URL = 'http://ndnmap.arl.wustl.edu/json/geocode/'

# conversion factor km -> mi
KM_TO_MI = 0.621371

def handle_request():
    loc_provided = "lat" in request.args and "lon" in request.args
    k_provided = "k" in request.args
    
    if loc_provided:
	loc = get_loc(request.args["lat"], request.args["lon"])
	if loc == None:
	    return "ERROR: Invalid lat/lon"
    
    if k_provided:
	try:
	    k = int(request.args["k"])
	    if k > 10:
		k = 10
	except ValueError:
	    return "ERROR: Invalid k: %s" % request.args["k"]
    else:
	k = 1
    
    IP = request.remote_addr
    s = ""
    if not loc_provided:
	if verbose:
	    s += req_info(IP)
	closest = getclosesthubs(IP, k)
    else:
	if verbose:
	    s += req_loc_info(loc)
	closest = getclosesthubs(IP, k, loc)
    
    return s + closest

class NamedLoc:
    name = ''
    fullname = ''
    loc = ()
    def __init__(self, name, fullname, loc, site):
	self.name = name
	self.fullname = fullname
	self.loc = loc
	self.site = site
    def __len__(self):
	return 2
    def __getitem__(self, key):
	return self.loc[key]
    def __str__(self):
	return self.name + ': ' + str(self.loc) + ', ' + str(self.site)
    def dump(self):
	return self.name, self.fullname, self.loc[0], self.loc[1], self.site

def get_loc(lat, lon):
    try:
	lat = float(lat)
	lon = float(lon)
	
	# check to make sure the latitude and longitude values are valid
	if lat < -90. or lat > 90. or lon < -180. or lon > 180.:
	    return None
	
	return (lat, lon)
    except ValueError:
	return None

def kdtsearch(loc, k=1):
    if k == 1:
	res = kdt.search_nn(loc)
	return [(res[0].data.dump(), res[1])]
    else:
	result_list = []
	res = kdt.search_knn(loc, k)
	for r in res:
	    result_list.append((r[0].data.dump(), r[1]))
	return result_list

def ascii(s):
    return s.encode('ASCII','ignore')

def confirm(s):
    try:
	return raw_input(s)[0].lower() == 'y'
    except IndexError:
	print "Please enter 'y' or 'n'"
	return confirm(s)

def fetch_wustl_geocode():
    with open('wustl-geocode.json', 'wb') as f:
	c = pycurl.Curl()
	c.setopt(c.URL, WUSTL_GEOCODE_URL)
	c.setopt(c.WRITEDATA, f)
	c.perform()
	c.close()

def convert_and_pickle_geocode():
    global geocode
    print 'Converting JSON file...'
    raw_data = json.load(open('wustl-geocode.json'))
    geocode = {
        ascii(k) :
        [ascii(v['name']), v['_real_position'], ascii(v['site'])]
        if '_real_position' in v 
        else [ascii(v['name']), v['position'], ascii(v['site'])]
        for k,v in raw_data.iteritems()
    }
    pickle.dump(geocode, open('gc.pkl', 'wb'))  
    print 'Succesfully dumped pickle.'

def initialize_kdt():
    global geocode
    print 'Building KD-Tree...'
    
    should_fetch = False
    
    try:
	geocode = pickle.load(open('gc.pkl', 'rb'))
	print 'Pickle file located and loaded.'
	if prompt_for_fetch and confirm('Discard pickle and fetch WUSTL Geocode JSON? (y/n): '):
	    should_fetch = True
    except IOError:
	print 'No pickle file found.'
	try:
	    raw_data = json.load(open('wustl-geocode.json'))
	    if confirm('A JSON Geocode file has been downloaded. ' +\
	               'Generate tree from this file? (y/n): '):
		convert_and_pickle_geocode()
	    else:
		should_fetch = True
	except IOError:
	    # if no pickle or local json exists, fetch the geocode remotely
	    print 'No JSON Geocode file is present.'
	    should_fetch = True
	
    # Fetch WUSTL Geocode JSON
    if should_fetch:
	print 'Fetching WUSTL Geocode JSON...'
	fetch_wustl_geocode()
	convert_and_pickle_geocode()
    
    kdt = kdtree.create([NamedLoc(k, v[0], v[1], v[2]) for k,v in geocode.iteritems()])
    #kdtree.visualize(kdt)
    return kdt

def req_info(IP):
    req_info = "\n>> %s - Request IP: %s\n\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), IP)
    print req_info
    return req_info

def req_loc_info(loc):
    req_info = "\n>> %s - Request location: (%f, %f)\n\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), loc[0], loc[1])
    print req_info
    return req_info

def mm_response_info(response):
    response_info = "MaxMind Response Information:\n"
    response_info += "  Continent: %s - %s (ID: %d)\n" % (response.continent.code, response.continent.names['en'], response.continent.geoname_id)
    response_info += "  Country: %s - %s (ID: %d)\n" % (response.country.iso_code, response.country.names['en'], response.country.geoname_id)
    for subdivision in response.subdivisions:
	response_info += "  Subdivision: %s - %s (ID: %d)\n" % (subdivision.iso_code, subdivision.names['en'], subdivision.geoname_id)
    if response.city.geoname_id is None:
	response_info += "\n  Warning: No City match found!\n"
    else:
	response_info += "  City: %s (ID: %d)" % (response.city.names['en'], response.city.geoname_id)
    response_info += "\n  Approximate Location: (%f, %f) with accuracy radius ~%d mi.\n" % (response.location.latitude, response.location.longitude, response.location.accuracy_radius * KM_TO_MI)
    #print response_info
    return response_info

def ip_to_loc(ip):
    response = reader.city(ip)
    loc = (response.location.latitude, response.location.longitude)
    if verbose:
	return loc, mm_response_info(response)
    else:
	print mm_response_info(response)
	return loc, ""

def dump(*list):
    result = ""
    for element in list:
	result += (element if type(element) is str else str(element)) + " "

def search_sum(result_list):
    template = "  %s - %s at (%f, %f)\n    Site: %s\n"
    n = len(result_list)
    s = "Closest Hub:\n" if (n == 1) else "\nClosest Hubs:\n"

    for result, dist in result_list:
	s += template % result
    return s

def getclosesthubs(IP, k=1, loc=None):

    verbose_temp = "%s%s\nResponse: %s\n"
    
    if loc is None:
	loc, mm_verbose = ip_to_loc(IP)
    else:
	mm_verbose = ""
    result_list = kdtsearch(loc, k)
    
    search_verbose = ""
    if verbose:
	search_verbose = search_sum(result_list)
    else:
	print search_sum(result_list)
    
    hubs = ""
    
    for result, dist in result_list:
	closesthub = result[-1]
	hubs += clean_site(closesthub) + ","
    
    if verbose:
	return verbose_temp % (mm_verbose, search_verbose, hubs[:-1])
    else:
	return hubs[:-1]

def clean_site(site):
    cleaned = site[site.find('//')+2:]
    if cleaned.endswith(':80/'):
	cleaned = cleaned[:-4]
    return cleaned    

   
reader = geoip2.database.Reader(MMDB_LOCATION)
kdt = initialize_kdt()

app = Flask(__name__)

@app.route('/hub')
def hub_req():
    global verbose
    verbose = False
    return handle_request(), 200, {'Content-Type': 'text/plain; charset=us-ascii'}

@app.route('/verbose')
def verbose_req():
    global verbose
    verbose = True
    return handle_request(), 200, {'Content-Type': 'text/plain; charset=us-ascii'}