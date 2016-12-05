NDN-FCH (Find Closest Hub)
==========================

NDN-FCH (Find Closest Hub) is a geolocation service application for the Named Data Networking (NDN) network. It aims to provide end hosts connecting to the NDN hub network with the ability to quickly locate the NDN hub closest to their current location.

## Prerequisites

- Python 3
- The following modules:

        pip install geoip2, kdtree, json, pycurl

- Download MaxMind GeoLite2-City database

        wget http://geolite.maxmind.com/download/geoip/database/GeoLite2-City.mmdb.gz
        gunzip GeoLite2-City.mmdb.gz
Download http://geolite.maxmind.com/download/geoip/database/GeoLite2-City.mmdb.gz and unzip the file GeoLite2-City.mmdb to the local directory.

## Running the server

     sudo nohup python /PATH/TO/FILE/ndn_fch_server.py &
