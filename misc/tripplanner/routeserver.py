from servable import Servable
from graphserver.graphdb import GraphDatabase
import cgi
from graphserver.core import State, WalkOptions, ContractionHierarchy, Combination
import time
import sys
import graphserver
from graphserver.util import TimeHelpers
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.ext.osm.profiledb import ProfileDB
from xml.dom.minidom import Document
try:
  import json
except ImportError:
  import simplejson as json

import settings
from glineenc import encode_pairs
from profile import Profile

from shortcut_cache import get_ep_geom, get_encoded_ep_geom, ShortcutCache, get_ep_profile, get_full_route_narrative

def reincarnate_ch(basename):
    chdowndb = GraphDatabase( basename+".down.gdb" )
    chupdb = GraphDatabase( basename+".up.gdb" )
    
    upgg = chupdb.incarnate()
    downgg = chdowndb.incarnate()
    
    return ContractionHierarchy(upgg, downgg)

class RouteServer(Servable):
    def __init__(self, ch_basename, osmdb_filename, profiledb_filename):
        graphdb = GraphDatabase( graphdb_filename )
        self.osmdb = OSMDB( osmdb_filename )
        self.profiledb = ProfileDB( profiledb_filename )
        self.ch = reincarnate_ch( ch_basename )
        self.shortcut_cache = ShortcutCache( ch_basename+".scc" )
    
    def vertices(self):
        return "\n".join( [vv.label for vv in self.graph.vertices] )
    vertices.mime = "text/plain"

    def path(self, lat1, lng1, lat2, lng2, transfer_penalty=0, walking_speed=1.0, hill_reluctance=1, narrative=True, jsoncallback=None):
        
        t0 = time.time()
        origin = "osm-%s"%self.osmdb.nearest_node( lat1, lng1 )[0]
        dest = "osm-%s"%self.osmdb.nearest_node( lat2, lng2 )[0]
        endpoint_find_time = time.time()-t0
        
        print origin, dest
        
        t0  = time.time()
        wo = WalkOptions()
        #wo.transfer_penalty=transfer_penalty
        #wo.walking_speed=walking_speed
        wo.walking_speed=5
        wo.walking_overage = 0
        wo.hill_reluctance = 20
        wo.turn_penalty = 15 
        
        edgepayloads = self.ch.shortest_path( origin, dest, State(1,0), wo )
        
        wo.destroy()
        
        route_find_time = time.time()-t0
        
        t0 = time.time()
        names = []
        geoms = []
        
        profile = Profile()
        total_dist = 0
        total_elev = 0
        
        if narrative:
            names, total_dist = get_full_route_narrative( self.osmdb, edgepayloads )
        
        for edgepayload in edgepayloads:
            geom, profile_seg = self.shortcut_cache.get( edgepayload.external_id )
            
            #geom = get_ep_geom( self.osmdb, edgepayload )
            #profile_seg = get_ep_profile( self.profiledb, edgepayload )

            geoms.extend( geom )
            profile.add( profile_seg )
            
        route_desc_time = time.time()-t0

        ret = json.dumps( (names, 
                           encode_pairs( [(lat, lon) for lon, lat in geoms] ), 
                           profile.concat(300),
                           { 'route_find_time':route_find_time,
                             'route_desc_time':route_desc_time,
                             'endpoint_find_time':endpoint_find_time,},
                           { 'total_dist':total_dist,
                             'total_elev':total_elev}) )

	ret2 = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Ri>\n"
	for name in names:
		ret2 = "%s<d>"% (ret2)
		for indy in name:
			if str(indy) != "0":
				if (type(indy) == tuple):
					onlon = True;
				else:
					indy = indy.capitalize()
					ret2 = "%s %s"% (ret2, indy)
					
		ret2 = "%s</d>\n"% (ret2)

	ret2 = "%s<r>\n"% (ret2)
	for lon, lat in geoms:
		ret2 = "%s<l>%s</l>\n"%(ret2,lat)
		ret2 = "%s<o>%s</o>\n"%(ret2,lon)

        #new stuff to find elevation
	profiley = profile
	latestpoint, latestelev = profiley.segs[0][0]
	lastleg = profiley.segs[len(profiley.segs)-1]

	lastpoint, lastelev = lastleg[len(lastleg)-1]
	elevchange = lastelev - latestelev;
	elevgain = 0;
	distance = 0;
	for seg in profiley.segs:
		for datapoint in range(len(seg)):
			point, elev = seg[datapoint]
			#ret2 = "%s<point0>%s<elev0>%s\n"%(ret2,point,elev)
			if(elev > latestelev):
				elevgain = elevgain + (elev - latestelev)
			latestelev = elev
		distance = distance + seg[len(seg)-1][0]
	ret2 = "%s</r>\n<cl>%s</cl>\n<ec>%s</ec>\n<di>%s</di>\n</Ri>"%(ret2,elevgain,elevchange,distance)

	doc = Document()

	# Create the <wml> base element
	#wml = doc.createElement("wml")
	#doc.appendChild(wml)

	# Create the main <card> element
	#maincard = doc.createElement("card")
	#maincard.setAttribute("id", "main")
	#wml.appendChild(maincard)

	# Create a <p> element
	#paragraph1 = doc.createElement("p")
	#maincard.appendChild(paragraph1)

	# Give the <p> elemenet some text
	#ptext = doc.createTextNode("This is a test!")
	#paragraph1.appendChild(ptext)

	# Print our newly created XML
	#print doc.toprettyxml(indent="  ")

        if jsoncallback:
            return "%s(%s)"%(jsoncallback,ret)
        else:
            return ret2
            #return doc.toxml("UTF-8")

    """
    def path_raw(self, origin, dest, currtime):
        
        wo = WalkOptions()
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path( dest )
        
        ret = "\n".join([str(x) for x in vertices]) + "\n\n" + "\n".join([str(x) for x in edges])

        spt.destroy()
        
        return ret
    """
        
    def bounds(self, jsoncallback=None):
        ret = json.dumps( self.osmdb.bounds() )
        if jsoncallback:
            return "%s(%s)"%(jsoncallback,ret)
        else:
            return ret

import sys
if __name__ == '__main__':
    
    usage = "python routeserver.py ch_basename osmdb_filename profiledb_filename thePort"
    
    if len(sys.argv) < 4:
        print usage
        exit()
        
    graphdb_filename = sys.argv[1]
    osmdb_filename = sys.argv[2]
    profiledb_filename = sys.argv[3]
    thePort = sys.argv[4]
    
    gc = RouteServer(graphdb_filename, osmdb_filename, profiledb_filename)
    gc.run_test_server(int(thePort))
