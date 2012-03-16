#Overview

This is how to setup this version of graphserver to work with OSM data to create a bike routing server.  The instructions below create a server running 9 instances of graphserver to do bike routing on a variety of hill and safety scenarios for the San Francisco Bay Area. Modify as needed.

You can see a live implementation and more documentation here: http://bikesy.com


##Create an EC2 instance "ami-48aa4921"

##setup prereqs
    $ yum install git-core
    $ yum install python-setuptools-devel
    $ yum install gcc
    $ yum install gcc-c++
    $ yum install python-devel
    $ easy_install simplejson

##get graphserver
    $ git clone git://github.com/bmander/graphserver.git

##get and switch to ch branch 
(ch is for Contraction Heirarchies http://en.wikipedia.org/wiki/Contraction_hierarchies)
    $ cd graphserver
    $ git fetch origin ch:ch
    $ git checkout ch

##install graphserver with python wrappers
    $ cd pygs
    $ python setup.py install

##install rtree
    $ cd ~
    $ mkdir downloads
    $ cd downloads
    $ wget http://download.osgeo.org/libspatialindex/spatialindex-src-1.7.1.tar.gz
    $ gunzip spatialindex-1.7.1.tar.gz
    $ tar -xvf spatialindex-1.7.1.tar
    $ cd spatialindex-1.7.1
    $ ./configure --prefix=/usr
    $ make
    $ make install
    $ easy_install RTree
    $ cp /usr/lib/python2.5/site-packages/Rtree-0.5.0-py2.5-linux-i686.egg/libsidx.so /usr/lib

OR on 64 bit systems

    $ easy_install http://pypi.python.org/packages/source/R/Rtree/Rtree-0.5.0.tar.gz#md5=fc9a23178bb031923a83fe213e6fdb25
    $ cp /usr/lib/python2.5/site-packages/Rtree-0.5.0-py2.5-linux-x86_64.egg/libsidx.so /usr/lib64

##install the latest version of servable
    $ cd ~
    $ yum install subversion
    $ svn checkout http://servable.googlecode.com/svn/trunk/ servable
    $ cd servable
    $ python setup.py install


##get java
    $ cd ~/downloads
    $ wget http://javadl.sun.com/webapps/download/AutoDL?BundleId=35674 -O java.bin
    $ chmod a+x java.bin
    $ ./java.bin


##get osmosis
    $ cd ~/downloads
    $ wget http://gweb.bretth.com/osmosis-latest.zip
    $ unzip osmosis-latest.zip
    $ chmod a+x osmosis-0.30/bin/osmosis


##create a 50 gig volume in the same zone as your instance


##mount the volume to a directory
    $ mkfs -t ext2 /dev/sdf
    $ mkdir /mnt/SF
    $ mount /dev/sdf /mnt/SF


##get california
    $ cd /mnt/SF
    $ wget http://downloads.cloudmade.com/americas/northern_america/united_states/california/california.highway.osm.bz2
    $ bunzip2 california.highway.osm.bz2

That there California is about 3.9 gigs.

##cut it down
    $ /root/downloads/osmosis-0.30/bin/osmosis --read-xml california.highway.osm --bounding-box left=-123.029 bottom=37.3064 right=-121.6370 top=38.3170 --write-xml bayarea.osm

##get DEM data from the USGS
    $ mkdir elevation

a) Download highest quality DEM available from seamless.usgs.gov, in GridFloat format
   - click "View & Download United States Data"
   - click the botton on the left that corresponds with "Define Download Area By Coordinates"
   - when a popup window comes up, click "Switch To Decimal Degrees"
   - key in your bounding box
   - a new popup will come up. Click "Modify Data Request"
   - Unselect everything except 1/3 arc-second DEM, in GridFloat format
   - It will give you several downloads, corresponding to different sections of the requested area. Download them all.

b) Unzip the gridfloats into their own folder


##make osmdb
    $ cd /mnt/SF
    $ gs_osmdb_compile bayarea.osm bayarea.osmdb


##compile profiledb
you have to pass in each of the flt files you downloaded above that cover every part of the area that you'd like route on.

    $ python /root/graphserver/misc/tripplanner/profile.py bayarea.osmdb bayarea.profiledb 10 elevation/04507044/04507044.flt elevation/06932766/06932766.flt elevation/26582513/26582513.flt elevation/55614802/55614802.flt elevation/59476301/59476301.flt elevation/77723440/77723440.flt elevation/82362642/82362642.flt elevation/94430404/94430404.flt


##Fold profiledb and osmdb into a compiled graph.  
Specify the weights you'd like to apply to each link type
    $ gs_compile_gdb -o bayarea.osmdb -p bayarea.profiledb -s "motorway:100" -s "motorway_link:100" -s "trunk:1.2" -s "trunk_link:1.2" -s "primary:1.1" -s "primary_link:1.1" -s "secondary:1" -s "secondary_link:1" -s "residential:1" -s "living_street:1" -s "steps:3" -s "track:1.1" -s "pedestrian:1.1" -s "path:1.1" -s "cycleway:0.9" -c "lane:0.9" -c "track:0.9" -c "path:0.9" -b "designated:0.9" -b "yes:0.9" -r "bicycle:0.9" -a "private:100" -a "no:100" bayarea.gdb

  -s - specifies an OSM highway key http://wiki.openstreetmap.org/wiki/Key:highway
  -c - specifies an OSM cycleway key http://wiki.openstreetmap.org/wiki/Key:cycleway
  -b - specifies an OSM bicycle key http://wiki.openstreetmap.org/wiki/Key:bicycle
  -r - specifies an OSM route key http://wiki.openstreetmap.org/wiki/Key:route
  -a - specifies an OSM access key http://wiki.openstreetmap.org/wiki/Key:access


#CREATING AN INDIVIDUAL ROUTESERVER

##Edit WalkOptions members in ch.py
for each set of contraction hierarchy graphs, edit the WalkOptions members in ch.py to suit your preferences, then:
    $ python /root/graphserver/misc/tripplanner/ch.py ./bayarea


##create the shortcut cache
    $ python /root/graphserver/misc/tripplanner/shortcut_cache.py ./bayarea


##run the routesever
    $ nohup sudo python ~/graphserver/misc/tripplanner/routeserver.py /mnt/SF/bayarea /mnt/SF/bayarea.osmdb /mnt/SF/bayarea.profiledb 8081


##make sure your port 80 is open, then:
view-source:http://ec2-184-73-96-123.compute-1.amazonaws.com:8081
view-source:http://ec2-184-73-96-123.compute-1.amazonaws.com:8081/bounds


##a sample API call is:

http://ec2-184-73-96-123.compute-1.amazonaws.com:8081/path?lng1=-122.42&lat1=37.75&lng2=-122.41&lat2=37.77

##Bounds for different Areas:
Bay Area:
38.317,-123.029 : 37.3064,-121.637

The Mission:
37.772,-122.428 : 37.733,-122.4

San Francisco:
37.9604,-122.5772 : 37.6746,-122.1151


#CREDITS
Brendan Martin Anderson https://github.com/bmander wrote most of these instuctions, I updated them to do what I needed.
