# Overview

This is how to setup this version of graphserver to work with OSM data to create a bike routing server.  The instructions below create a server running 9 instances of graphserver to do bike routing on a variety of hill and safety scenarios for the San Francisco Bay Area. Modify as needed.

You can see a live implementation and more documentation here: http://bikesy.com

## EC2 setup
If you want to use Amazon EC2 to host graphserver, here are the steps
* Create an EC2 instance "amzn-ami-pv-2016.03.1.x86_64-ebs (ami-8ff710e2)"
* Create a 50 gig volume in the same zone as your instance
* Mount the volume to a directory
    sudo mkfs -t ext4 /dev/xvdf
    sudo mkdir /mnt/SF
      sudo mount /dev/xvdf /mnt/SF

## Setup prereqs
    sudo yum install git gcc gcc-c++ python-setuptools

## Get graphserver
    git clone https://github.com/brendannee/Bikesy-Backend
    cd Bikesy-Backend

## Install graphserver with python wrappers
    cd pygs
    sudo python setup.py install

## Install libspatialindex
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

## Install rtree
    sudo pip install RTree

## Get osmosis
    cd ~/downloads
    wget http://bretth.dev.openstreetmap.org/osmosis-build/osmosis-latest.zip
    unzip osmosis-latest.zip
    chmod a+x bin/osmosis


## Download the OSM data
    cd /mnt/SF
    wget https://download.geofabrik.de/north-america/us/california-latest.osm.bz2
    bunzip2 california-latest.osm.bz2

## Merge OSM data if needed
If you are supporting more than one state, you'll need to merge it.

~/downloads/bin/osmosis --rx california-latest.osm  --rx nevada-latest.osm --merge --wx california-nevada.osm

## Cut it down
Choose your bounding box - here are some examples:
Bay Area:
    38.317,-123.029 : 37.3064,-121.637

The Mission:
    37.772,-122.428 : 37.733,-122.4

San Francisco:
    37.9604,-122.5772 : 37.6746,-122.1151

Lake Tahoe:
    39.368232, -120.345042 : 38.750276, -119.659482

Use Osmosis to cut it out.  Be sure to use the `completeWays=yes` option for `bounding-box`

    ~/downloads/bin/osmosis --read-xml california-latest.osm --bounding-box left=-123.029 bottom=37.3064 right=-121.6370 top=38.3170 completeWays=yes --tf accept-ways highway=* --write-xml bayarea.osm

    ~/downloads/bin/osmosis --read-xml us-pacific-latest.osm --bounding-box left=-120.345042 bottom=38.750276 right=-119.659482 top=39.368232 completeWays=yes --tf accept-ways highway=* --write-xml tahoe.osm

## Make osmdb
    gs_osmdb_compile bayarea.osm bayarea.osmdb

    gs_osmdb_compile tahoe.osm tahoe.osmdb

## Get DEM data from the USGS
    mkdir elevation

a) Download highest quality DEM available from http://nationalmap.gov/3DEP/index.html, in GridFloat format
   - click "Download Data"
   - select "Coordinates" and enter in your bounding box and click "Draw AOI"
   - Unselect everything except 1/3 arc-second DEM, in GridFloat format
   - It will give you several downloads, corresponding to different sections of the requested area. Download them all.

b) Unzip the gridfloats into their own folder

## Compile profiledb
Pass in each of the .flt files you downloaded above that cover every part of the area that you'd like route on.

    python ~/Bikesy-Backend/misc/tripplanner/profile.py bayarea.osmdb bayarea.profiledb 10 elevation/04507044/04507044.flt elevation/06932766/06932766.flt elevation/26582513/26582513.flt elevation/55614802/55614802.flt elevation/59476301/59476301.flt elevation/77723440/77723440.flt elevation/82362642/82362642.flt elevation/94430404/94430404.flt

    python ~/Bikesy-Backend/misc/tripplanner/profile.py tahoe.osmdb tahoe.profiledb 10 elevation/n39w120/floatn39w120_13.flt elevation/n39w121/floatn39w121_13.flt elevation/n40w120/floatn40w120_13.flt elevation/n40w121/floatn40w121_13.flt


## Fold profiledb and osmdb into a compiled graph
You have to pass in each of the flt files you downloaded above that cover every part of the area that you'd like route on.

Specify the weights you'd like to apply to each link type
    gs_compile_gdb -o bayarea.osmdb -p bayarea.profiledb -s "motorway:100" -s "motorway_link:100" -s "trunk:1.2" -s "trunk_link:1.2" -s "primary:1.1" -s "primary_link:1.1" -s "secondary:1" -s "secondary_link:1" -s "residential:1" -s "living_street:1" -s "steps:3" -s "track:1.1" -s "pedestrian:1.1" -s "path:1.1" -s "cycleway:0.9" -c "lane:0.9" -c "track:0.9" -c "path:0.9" -b "designated:0.9" -b "yes:0.9" -r "bicycle:0.9" -a "private:100" -a "no:100" bayarea.gdb

    gs_compile_gdb -o tahoe.osmdb -p tahoe.profiledb -s "motorway:100" -s "motorway_link:100" -s "trunk:1.2" -s "trunk_link:1.2" -s "primary:1.1" -s "primary_link:1.1" -s "secondary:1" -s "secondary_link:1" -s "residential:1" -s "living_street:1" -s "steps:3" -s "track:1.1" -s "pedestrian:1.1" -s "path:1.1" -s "cycleway:0.9" -c "lane:0.9" -c "track:0.9" -c "path:0.9" -b "designated:0.9" -b "yes:0.9" -r "bicycle:0.9" -a "private:100" -a "no:100" tahoe.gdb

  -s - specifies an OSM highway key http://wiki.openstreetmap.org/wiki/Key:highway
  -c - specifies an OSM cycleway key http://wiki.openstreetmap.org/wiki/Key:cycleway
  -b - specifies an OSM bicycle key http://wiki.openstreetmap.org/wiki/Key:bicycle
  -r - specifies an OSM route key http://wiki.openstreetmap.org/wiki/Key:route
  -a - specifies an OSM access key http://wiki.openstreetmap.org/wiki/Key:access

# Creating an Individual Route Server

## Edit WalkOptions members in ch.py
for each set of contraction hierarchy graphs, edit the WalkOptions numbers in ch.py to suit your preferences, then:
    python ~/Bikesy-Backend/misc/tripplanner/ch.py ./bayarea

    python ~/Bikesy-Backend/misc/tripplanner/ch.py ./tahoe


## Create the shortcut cache
    python ~/Bikesy-Backend/misc/tripplanner/shortcut_cache.py ./bayarea

    python ~/Bikesy-Backend/misc/tripplanner/shortcut_cache.py ./tahoe

## Install and configure Nginx

    easy_install uwsgi

    sudo yum install nginx

    vi /etc/nginx/nginx.conf

Find the location / section, and change it to as follow:

    location / {
        include uwsgi_params;
        uwsgi_pass 127.0.0.1:10080;
    }

Start nginx

    service nginx start
    chkconfig nginx on


## Run the routesever

    cd ~/Bikesy-Backend/misc/tripplanner
    uwsgi --yaml ./routeserver.yaml

## Stop the routeserver

    sudo kill -INT `cat /tmp/uwsgi.pid`

## Logs

    /var/log/nginx/error.log
    /var/log/wsgi.log

## Sample API call

http://ec2-52-39-88-148.us-west-2.compute.amazonaws.com/?lat1=39.10875135935859&lng1=-119.89242553710938&lat2=39.02345139405932&lng2=-119.9212646484375

# Restarting Server
## Remount EBS
    mount /dev/sdf /mnt/SF

## Run the routeserver
    cd /mnt/SF/bayarea

    # run all 9 servers
    nohup python routeserverONLY.py

    # run one specific server
    nohup sudo python /root/Bikesy-Backend/misc/tripplanner/routeserver.py ./bayarea ./bayarea.osmdb ./bayarea.profiledb 8081

## Run multiple routeservers

    sudo env "PATH=$PATH" python create.py

# Credits
Brendan Martin Anderson https://github.com/bmander wrote graphserver, the underlying system that handles the bike routing.


http://ec2-52-39-88-148.us-west-2.compute.amazonaws.com/?lat1=39.23757161784571&lng1=-120.10665893554688&lat2=39.25990481501755&lng2=-120.02151489257812
http://ec2-52-39-88-148.us-west-2.compute.amazonaws.com/?lat1=39.23757161784571

http://s3-us-west-1.amazonaws.com/tahoe-bike/index.html#
