# Bikesy Server

This is how to setup this version of graphserver to work with OSM data to create a bike routing server.  The instructions below create a server running 9 instances of graphserver to do bike routing on a variety of hill and safety scenarios for the San Francisco Bay Area. Modify as needed.

You can see a live implementation and more documentation here: http://bikesy.com

## Server setup

### EC2 setup
If you want to use Amazon EC2 to host graphserver, here are the steps
* Create an EC2 instance "amzn-ami-pv-2016.03.1.x86_64-ebs (ami-8ff710e2)"
* Create a 60 gig volume in the same zone as your instance
* Mount the volume to a directory
    sudo mkfs -t ext4 /dev/sdf
    sudo mkdir /mnt/bayarea
    sudo mount /dev/sdf /mnt/bayarea

### Setup prereqs
    sudo yum install git gcc gcc-c++ python-setuptools

### Get graphserver
    git clone https://github.com/brendannee/bikesy-server
    cd bikesy-server

### Install graphserver with python wrappers
    cd pygs
    sudo python setup.py install

### Install libspatialindex
    cd ~
    mkdir downloads
    cd ~/downloads
    wget http://download.osgeo.org/libspatialindex/spatialindex-src-1.8.5.tar.gz
    gunzip spatialindex-src-1.8.5.tar.gz
    tar -xvf spatialindex-src-1.8.5.tar
    cd spatialindex-src-1.8.5
    ./configure --prefix=/usr
    make
    sudo make install
    sudo /sbin/ldconfig

### Install rtree
    sudo pip install RTree

### Install osmosis
    cd ~/downloads
    wget http://bretth.dev.openstreetmap.org/osmosis-build/osmosis-latest.zip
    unzip osmosis-latest.zip
    chmod a+x bin/osmosis

## Data Preparation

### Download OSM data
Download data for the US states you want

    cd /mnt/SF
    wget https://download.geofabrik.de/north-america/us/nevada-latest.osm.bz2
    bunzip2 nevada-latest.osm.bz2

### Merge OSM data if needed
If you are supporting more than one state, you'll need to merge it.

    ~/downloads/bin/osmosis --rx california-latest.osm  --rx nevada-latest.osm --merge --wx california-nevada.osm

### Cut down the OSM data to a bounding box
Choose your bounding box - for example:

Bay Area:
    38.317,-123.029 : 37.3064,-121.637
    38.317,-122.8 : 37.3064,-121.637

The Mission:
    37.772,-122.428 : 37.733,-122.4

San Francisco:
    37.9604,-122.5772 : 37.6746,-122.1151

Lake Tahoe:
    39.368232, -120.345042 : 38.750276, -119.659482

Use Osmosis to cut out just the OSM data within your bounding box. Be sure to use the `completeWays=yes` option for `bounding-box`

    Bay Area:
    ~/downloads/bin/osmosis --read-xml california-latest.osm --bounding-box left=-122.8 bottom=37.3064 right=-121.637 top=38.0534 completeWays=yes --tf accept-ways highway=* --write-xml bayarea.osm

    The Mission:
    ~/downloads/bin/osmosis --read-xml california-latest.osm --bounding-box left=-122.428 bottom=37.733 right=-122.4 top=37.772 completeWays=yes --tf accept-ways highway=* --write-xml bayarea.osm

    Lake Tahoe:
    ~/downloads/bin/osmosis --read-xml california-nevada.osm --bounding-box left=-120.345042 bottom=38.750276 right=-119.659482 top=39.368232 completeWays=yes --tf accept-ways highway=* --tf reject-ways surface=dirt --write-xml tahoe.osm

### Make an osmdb file
    gs_osmdb_compile bayarea.osm bayarea.osmdb

    gs_osmdb_compile tahoe.osm tahoe.osmdb

### Get DEM data from the USGS
    mkdir elevation

a) Download highest quality DEM available from http://nationalmap.gov/3DEP/index.html, in GridFloat format
   - click "Download Data"
   - select "Coordinates" and enter in your bounding box and click "Draw AOI"
   - Unselect everything except 1/3 arc-second DEM, in GridFloat format
   - It will give you several downloads, corresponding to different sections of the requested area. Download them all.

b) Unzip the gridfloats into their own folder

### Compile a profiledb file
Pass in each of the .flt files you downloaded above that cover every part of the area that you'd like route on.

    Bay Area:
    python ~/bikesy-server/misc/tripplanner/profile.py bayarea.osmdb bayarea.profiledb 10 elevation/04507044/04507044.flt elevation/06932766/06932766.flt elevation/26582513/26582513.flt elevation/55614802/55614802.flt elevation/59476301/59476301.flt elevation/77723440/77723440.flt elevation/82362642/82362642.flt elevation/94430404/94430404.flt

    Tahoe:
    python ~/bikesy-server/misc/tripplanner/profile.py tahoe.osmdb tahoe.profiledb 10 elevation/n39w120/floatn39w120_13.flt elevation/n39w121/floatn39w121_13.flt elevation/n40w120/floatn40w120_13.flt  elevation/n40w121/floatn40w121_13.flt

### Optional: run create.py script to automate the following steps

    sudo python ~/bikesy-server/misc/tripplanner/create.py

### Fold profiledb and osmdb into a compiled graph

Specify the weights you'd like to apply to each link type

Bay Area:
    gs_compile_gdb -o bayarea.osmdb -p bayarea.profiledb -s "motorway:100" -s "motorway_link:100" -s "trunk:1.2" -s "trunk_link:1.2" -s "primary:1.1" -s "primary_link:1.1" -s "secondary:1" -s "secondary_link:1" -s "residential:1" -s "living_street:1" -s "steps:3" -s "track:1.1" -s "pedestrian:1.1" -s "path:1.1" -s "cycleway:0.9" -c "lane:0.9" -c "track:0.9" -c "path:0.9" -b "designated:0.9" -b "yes:0.9" -r "bicycle:0.9" -a "private:100" -a "no:100" bayarea.gdb

Tahoe Low:
    gs_compile_gdb -o tahoe.osmdb -p tahoe.profiledb -s "motorway:100" -s "motorway_link:100" -s "trunk:1.2" -s "trunk_link:1.2" -s "primary:1.1" -s "primary_link:1.1" -s "secondary:1" -s "secondary_link:1" -s "residential:1" -s "living_street:1" -s "steps:3" -s "track:1.1" -s "pedestrian:1.1" -s "path:0.8" -s "cycleway:0.8" -c "lane:0.9" -c "track:0.9" -c "path:0.8" -b "designated:0.9" -b "yes:0.9" -r "bicycle:0.9" -a "private:100" -a "no:100" tahoe.gdb

Tahoe High:
    gs_compile_gdb -o tahoe.osmdb -p tahoe.profiledb -s "motorway:100" -s "motorway_link:100" -s "trunk:1.5" -s "trunk_link:1.5" -s "primary:1.4" -s "primary_link:1.4" -s "secondary:1.2" -s "secondary_link:1.2" -s "residential:.9" -s "living_street:.9" -s "steps:2" -s "track:.9" -s "pedestrian:1" -s "path:0.5" -s "cycleway:0.5" -c "lane:0.6" -c "track:0.6" -c "path:0.5" -b "designated:0.6" -b "yes:0.6" -r "bicycle:0.6" -a "private:100" -a "no:100" tahoe.gdb

  -s - specifies an OSM highway key http://wiki.openstreetmap.org/wiki/Key:highway
  -c - specifies an OSM cycleway key http://wiki.openstreetmap.org/wiki/Key:cycleway
  -b - specifies an OSM bicycle key http://wiki.openstreetmap.org/wiki/Key:bicycle
  -r - specifies an OSM route key http://wiki.openstreetmap.org/wiki/Key:route
  -a - specifies an OSM access key http://wiki.openstreetmap.org/wiki/Key:access


### Edit WalkOptions members in ch.py
For each set of contraction hierarchy graphs, edit the WalkOptions numbers in ch.py to suit your preferences, then:
    python ~/bikesy-server/misc/tripplanner/ch.py ./bayarea

    python ~/bikesy-server/misc/tripplanner/ch.py ./tahoe

### Create the shortcut cache
    python ~/bikesy-server/misc/tripplanner/shortcut_cache.py ./bayarea

    python ~/bikesy-server/misc/tripplanner/shortcut_cache.py ./tahoe

### Setup config file

    cd ~/bikesy-server/misc/tripplanner
    cp config-example.json config.json

Edit `config.json` as needed.

## Setup the web server

### Install and configure Nginx

    pip install uwsgi

    sudo yum install nginx

    sudo vi /etc/nginx/nginx.conf

Find the location / section, and change it to as follow:

    location / {
        include uwsgi_params;
        uwsgi_pass 127.0.0.1:10080;
    }

### Start nginx

    sudo service nginx start
    sudo chkconfig nginx on


### Run the routesever

    cd ~/bikesy-server/misc/tripplanner
    uwsgi --yaml ./routeserver.yaml

To see what is going on, tail the Logs

    tail /var/log/uwsgi.log -f

### Sample API call

http://ec2-52-39-88-148.us-west-2.compute.amazonaws.com/?lat1=39.147547&lng1=-120.162651&lat2=39.0169036&lng2=-120.1256955&scenario=1

## Manage the web server

### Stop the routeserver

    sudo service nginx stop
    sudo kill -INT `cat /tmp/uwsgi.pid`

or

    killall -s INT uwsgi

### Review Logs

    /var/log/nginx/error.log
    /var/log/uwsgi.log

## Create Bike facility overlays from OSM file

    ~/downloads/bin/osmosis --read-xml tahoe.osm --tf accept-ways highway=path,cycleway --tf accept-ways bicycle=designated --tf reject-relations --used-node --write-xml class1-1.osm
    ~/downloads/bin/osmosis --read-xml tahoe.osm --tf accept-ways highway=footway --tf accept-ways bicycle=yes --tf reject-relations --used-node --write-xml class1-2.osm
    ~/downloads/bin/osmosis --read-xml class1-1.osm --rx class1-2.osm --merge --wx class1.osm

    ~/downloads/bin/osmosis --read-xml tahoe.osm --tf accept-ways highway=residential,unclassified,tertiary,secondary,primary,trunk --tf accept-ways cycleway=lane --tf reject-relations --used-node --write-xml class2-1.osm
    ~/downloads/bin/osmosis --read-xml tahoe.osm --tf accept-ways highway=residential,unclassified,tertiary,secondary,primary,trunk --tf accept-ways cycleway:left=lane --tf reject-relations --used-node --write-xml class2-2.osm
    ~/downloads/bin/osmosis --read-xml tahoe.osm --tf accept-ways highway=residential,unclassified,tertiary,secondary,primary,trunk --tf accept-ways cycleway:right=lane --tf reject-relations --used-node --write-xml class2-3.osm
    ~/downloads/bin/osmosis --read-xml class2-1.osm --rx class2-2.osm --rx class2-3.osm --merge --wx class2.osm

    ~/downloads/bin/osmosis --read-xml tahoe.osm --tf accept-ways lcn=yes --tf reject-ways bicycle=designated --tf reject-ways highway=footway --tf reject-ways cycleway=lane --tf reject-relations --used-node --write-xml class3-1.osm
    ~/downloads/bin/osmosis --read-xml tahoe.osm --tf accept-ways highway=residential,unclassified,tertiary,secondary,primary,trunk --tf accept-ways cycleway=shared_lane --tf reject-ways cycleway=lane --tf reject-relations --used-node --write-xml class3-2.osm
    ~/downloads/bin/osmosis --read-xml class3-1.osm --rx class3-2.osm --merge --wx class3.osm

    npm install -g simplify-geojson minify-geojson

    cat class1.geojson | simplify-geojson -t 0.00001 > class1.simple.geojson
    minify-geojson -w "name" -c 5 class1.simple.geojson

## Credits
Brendan Martin Anderson https://github.com/bmander wrote graphserver, the underlying system that handles the bike routing.
