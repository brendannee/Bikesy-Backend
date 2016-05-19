# Overview

This is how to setup this version of graphserver to work with OSM data to create a bike routing server.  The instructions below create a server running 9 instances of graphserver to do bike routing on a variety of hill and safety scenarios for the San Francisco Bay Area. Modify as needed.

You can see a live implementation and more documentation here: http://bikesy.com


## EC2 setup
If you want to use Amazon EC2 to host graphserver, here are the steps
* Create an EC2 instance "amzn-ami-pv-2016.03.1.x86_64-ebs (ami-8ff710e2)"
* Create a 50 gig volume in the same zone as your instance
* Mount the volume to a directory
    mkfs -t ext2 /dev/sdf
    sudo mkdir /mnt/SF
    sudo mount /dev/sdf /mnt/SF


## Setup prereqs
    sudo yum install git
    sudo yum install gcc
    sudo yum install gcc-c++
    sudo yum install python-setuptools

    <!--
    $ yum install gcc-c++
    $ yum install python-devel
    $ easy_install simplejson -->

## Get graphserver
    git git clone https://github.com/brendannee/Bikesy-Backend
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
    make install
    sudo /sbin/ldconfig

## Install rtree
    pip install RTree
<!--
## Install the latest version of servable
    pip install servable -->

## Get osmosis
    cd ~/downloads
    wget http://bretth.dev.openstreetmap.org/osmosis-build/osmosis-latest.zip
    unzip osmosis-latest.zip
    chmod a+x bin/osmosis


## Download the OSM data
    cd /mnt/SF
    wget https://download.geofabrik.de/north-america/us/california-latest.osm.bz2
    bunzip2 california-latest.osm.bz2

That there California is about 3.9 gigs.

## Cut it down
Choose your bounding box - here are some examples:
Bay Area:
    38.317,-123.029 : 37.3064,-121.637

The Mission:
    37.772,-122.428 : 37.733,-122.4

San Francisco:
    37.9604,-122.5772 : 37.6746,-122.1151

Use Osmosis to cut it out.  Be sure to use the `completeWays=yes` option for `bounding-box`

    ~/downloads/bin/osmosis --read-xml california-latest.osm --bounding-box left=-123.029 bottom=37.3064 right=-121.6370 top=38.3170 completeWays=yes --write-xml bayarea.osm

## Get DEM data from the USGS
    mkdir elevation

a) Download highest quality DEM available from seamless.usgs.gov, in GridFloat format
   - click "Seamless Viewer"
   - click the bottom on the left that corresponds with "Define Download Area By Coordinates"
   - when a popup window comes up, click "Switch To Decimal Degrees"
   - key in your bounding box
   - a new popup will come up. Click "Modify Data Request"
   - Unselect everything except 1/3 arc-second NED, in GridFloat format
   - It will give you several downloads, corresponding to different sections of the requested area. Download them all.

b) Unzip the gridfloats into their own folder

## Make osmdb
    cd /mnt/SF
    gs_osmdb_compile bayarea.osm bayarea.osmdb

## Compile profiledb
Pass in each of the .flt files you downloaded above that cover every part of the area that you'd like route on.

    python ~/Bikesy-Backend/misc/tripplanner/profile.py bayarea.osmdb bayarea.profiledb 10 elevation/04507044/04507044.flt elevation/06932766/06932766.flt elevation/26582513/26582513.flt elevation/55614802/55614802.flt elevation/59476301/59476301.flt elevation/77723440/77723440.flt elevation/82362642/82362642.flt elevation/94430404/94430404.flt


## Fold profiledb and osmdb into a compiled graph
Specify the weights you'd like to apply to each link type
    gs_compile_gdb -o bayarea.osmdb -p bayarea.profiledb -s "motorway:100" -s "motorway_link:100" -s "trunk:1.2" -s "trunk_link:1.2" -s "primary:1.1" -s "primary_link:1.1" -s "secondary:1" -s "secondary_link:1" -s "residential:1" -s "living_street:1" -s "steps:3" -s "track:1.1" -s "pedestrian:1.1" -s "path:1.1" -s "cycleway:0.9" -c "lane:0.9" -c "track:0.9" -c "path:0.9" -b "designated:0.9" -b "yes:0.9" -r "bicycle:0.9" -a "private:100" -a "no:100" bayarea.gdb

  -s - specifies an OSM highway key http://wiki.openstreetmap.org/wiki/Key:highway
  -c - specifies an OSM cycleway key http://wiki.openstreetmap.org/wiki/Key:cycleway
  -b - specifies an OSM bicycle key http://wiki.openstreetmap.org/wiki/Key:bicycle
  -r - specifies an OSM route key http://wiki.openstreetmap.org/wiki/Key:route
  -a - specifies an OSM access key http://wiki.openstreetmap.org/wiki/Key:access

## Compile profiledb
you have to pass in each of the flt files you downloaded above that cover every part of the area that you'd like route on.

# Creating an Individual Route Server

## Edit WalkOptions members in ch.py
for each set of contraction hierarchy graphs, edit the WalkOptions numbers in ch.py to suit your preferences, then:
    $ python ~/Bikesy-Backend/misc/tripplanner/ch.py ./bayarea


## Create the shortcut cache
    $ python ~/Bikesy-Backend/misc/tripplanner/shortcut_cache.py ./bayarea


## Run the routesever
    $ sudo python ~/Bikesy-Backend/misc/tripplanner/routeserver.py /mnt/SF/bayarea/bayarea /mnt/SF/bayarea/bayarea.osmdb /mnt/SF/bayarea/bayarea.profiledb 8081

if its for production, you could run

    $ nohup sudo python ~/Bikesy-Backend/misc/tripplanner/routeserver.py /mnt/SF/bayarea /mnt/SF/bayarea.osmdb /mnt/SF/bayarea.profiledb 8081

## Make sure your port 80 is open, then:
view-source:http://ec2-184-73-96-123.compute-1.amazonaws.com:8081
view-source:http://ec2-184-73-96-123.compute-1.amazonaws.com:8081/bounds

## Sample API call

http://ec2-184-73-96-123.compute-1.amazonaws.com:8081/path<D-c>?lng1=-122.42&lat1=37.75&lng2=-122.41&lat2=37.77


# Restarting Server
## Remount EBS
    mount /dev/sdf /mnt/SF

## Run the routeserver
    cd /mnt/SF/bayarea

    # run all 9 servers
    nohup python routeserverONLY.py

    # run one specific server
    nohup sudo python /root/Bikesy-Backend/misc/tripplanner/routeserver.py ./bayarea ./bayarea.osmdb ./bayarea.profiledb 8081

# Credits
Brendan Martin Anderson https://github.com/bmander wrote most of these instuctions, I updated them to do what I needed.
