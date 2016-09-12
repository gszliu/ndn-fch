import time
from pyndn import Name
from pyndn import Data
from pyndn import Face
from pyndn.security import KeyChain

import geoip2.database
import kdtree
import json
import cPickle as pickle
import pycurl

isWindows = True

MMDB_LOCATION = 'GeoLite2-City.mmdb'
WUSTL_GEOCODE_URL = 'http://ndnmap.arl.wustl.edu/json/geocode/'
NDN_PREFIX = '/ndn/edu/ucla/cs/gszliu/ndn-fch'

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
        return self.name, self.fullname, self.loc, self.site

def kdtsearch(t, loc):
    return t.search_nn(loc)[0].data.dump()

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
    print 'Building KD-Tree...'
    
    should_fetch = False
    
    try:
        geocode = pickle.load(open('gc.pkl', 'rb'))
	print 'Pickle file located and loaded.'
	if confirm('Discard pickle and fetch WUSTL Geocode JSON? (y/n): '):
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

def ip_to_loc(ip, reader):
    # ##############################################
    #     DB COVERT
    # ##############################################
    response = reader.city(ip)
    loc = (response.location.latitude, response.location.longitude)
    return loc

def dump(*list):
    result = ""
    for element in list:
        result += (element if type(element) is str else str(element)) + " "
    print(result)

class Echo(object):
    def __init__(self, keyChain, certificateName):
        self._keyChain = keyChain
        self._certificateName = certificateName
        self._responseCount = 0
        self.reader = geoip2.database.Reader(MMDB_LOCATION)
        self.kdt = initialize_kdt()

    def onInterest(self, prefix, interest, face, interestFilterId, filter):
        self._responseCount += 1

        # Make and sign a Data packet.
	name = interest.getName()
	IP_comp = name.get(-1)
	IP = str(IP_comp.getValue())
        data = Data(interest.getName())

	loc = ip_to_loc(IP, self.reader)
        result = kdtsearch(self.kdt, loc)

	closesthub = result[-1]
	closesthub_id = closesthub[closesthub.find('//')+2:]
	if closesthub_id.endswith(':80/'):
		closesthub_id = closesthub_id[:-4]

        data.setContent(closesthub_id)

        self._keyChain.sign(data, self._certificateName)

	print '\nReceived interest with IP: %s'%IP
	print 'Found closest hub:'
	print '   Hub:      %s'%result[0]
	print '   Name:     %s'%result[1]
	print '   Location: (%f, %f)'%(result[2][0], result[2][1])
	print 
	print 'Sending hub %s for IP %s'%(closesthub_id, IP)        

	face.putData(data)

    def onRegisterFailed(self, prefix):
        self._responseCount += 1
        dump("Register failed for prefix", prefix.toUri())

def main():
    # The default Face will connect using a Unix socket, or to "localhost".
    face = Face()

    # Use the system default key chain and certificate name to sign commands.
    keyChain = KeyChain()
    face.setCommandSigningInfo(keyChain, keyChain.getDefaultCertificateName())

    # Also use the default certificate name to sign data packets.
    echo = Echo(keyChain, keyChain.getDefaultCertificateName())
    prefix = Name(NDN_PREFIX)
    dump("Register prefix", prefix.toUri())
    face.registerPrefix(prefix, echo.onInterest, echo.onRegisterFailed)

    while True:# echo._responseCount < 1:
        try:
		face.processEvents()
        	# We need to sleep for a few milliseconds so we don't use 100% of the CPU.
        	time.sleep(0.01)
	except KeyboardInterrupt:
		print 'KeyboardInterrupt, breaking'
		break
    face.shutdown()

main()
