from flask import Flask, request
from flask_cors import CORS
from graphserver.graphdb import GraphDatabase
from graphserver.core import State, WalkOptions, ContractionHierarchy
import time
import graphserver
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.ext.osm.profiledb import ProfileDB

try:
    import json
except ImportError:
    import simplejson as json

from glineenc import encode_pairs
from profile import Profile

from shortcut_cache import get_ep_geom, get_encoded_ep_geom, ShortcutCache, get_ep_profile, get_full_route_narrative

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
CORS(app)

def reincarnate_ch(basename):
    chdowndb = GraphDatabase(basename + ".down.gdb")
    chupdb = GraphDatabase(basename + ".up.gdb")

    upgg = chupdb.incarnate()
    downgg = chdowndb.incarnate()

    return ContractionHierarchy(upgg, downgg)

with open('config.json') as json_data_file:
    settings = json.load(json_data_file)

scenarios = settings['scenarios']

# graphdb = {}
osmdb = {}
# profiledb = {}
ch = {}
shortcut_cache = {}

for scenario in scenarios:
    id = scenario['id']
    basename = scenario['basename']

    # graphdb[id] = GraphDatabase(basename)
    osmdb[id] = OSMDB(basename + ".osmdb")
    # profiledb[id] = ProfileDB(basename + ".profiledb")
    ch[id] = reincarnate_ch(basename)
    shortcut_cache[id] = ShortcutCache(basename + ".scc")


def handleError(message):
    return json.dumps({'error': message})


@app.route('/')
def routeserver():
    lat1 = request.args.get('lat1')
    lat2 = request.args.get('lat2')
    lng1 = request.args.get('lng1')
    lng2 = request.args.get('lng2')
    scenario = request.args.get('scenario')

    if not lat1:
        return handleError('No `lat1` specified')
    if not lat2:
        return handleError('No `lat2` specified')
    if not lng1:
        return handleError('No `lng1` specified')
    if not lng2:
        return handleError('No `lng2` specified')
    if not scenario:
        scenario = '1'

    lat1 = float(lat1)
    lat2 = float(lat2)
    lng1 = float(lng1)
    lng2 = float(lng2)

    t0 = time.time()
    origin_nearest_node = osmdb[scenario].nearest_node(lat1, lng1)
    dest_nearest_node = osmdb[scenario].nearest_node(lat2, lng2)

    origin = "osm-%s" % origin_nearest_node[0]
    dest = "osm-%s" % dest_nearest_node[0]
    endpoint_find_time = time.time() - t0

    print origin, dest

    t0 = time.time()
    wo = WalkOptions()
    wo.walking_speed = 5
    wo.walking_overage = 0
    wo.hill_reluctance = 20
    wo.turn_penalty = 15

    edgepayloads = ch[scenario].shortest_path(origin, dest, State(1, 0), wo)

    wo.destroy()

    route_find_time = time.time() - t0

    t0 = time.time()
    directions = []
    geoms = []

    profile = Profile()

    directions, total_dist = get_full_route_narrative( osmdb[scenario], edgepayloads )

    for edgepayload in edgepayloads:
        geom, profile_seg = shortcut_cache[scenario].get(edgepayload.external_id)

        #geom = get_ep_geom( osmdb[scenario], edgepayload )
        #profile_seg = get_ep_profile( profiledb[scenario], edgepayload )

        geoms.extend(geom)
        profile.add(profile_seg)

    route_desc_time = time.time() - t0

    return json.dumps({'directions': directions,
                       'path': encode_pairs([(lat, lon) for lon, lat in geoms]),
                       'elevation_profile': profile.concat(300),
                       'total_distance': total_dist,
                       'stats': {
                           'route_find_time': route_find_time,
                           'route_desc_time': route_desc_time,
                           'endpoint_find_time': endpoint_find_time,
                        }})

@app.route('/bounds')
def bounds():
    bounds = osmdb.bounds()
    return json.dumps({
        'left': bounds[0],
        'bottom': bounds[1],
        'right': bounds[2],
        'top': bounds[3]
    })

if __name__ == '__main__':
    app.run()
