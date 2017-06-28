import os

try:
    import json
except ImportError:
    import simplejson as json

bikesy_base = '/home/ec2-user/bikesy-server'

with open(bikesy_base + '/misc/tripplanner/config.json') as json_data_file:
    settings = json.load(json_data_file)

scenarios = settings['scenarios']

os.system('mkdir -p ' + settings['basename'] + '/scenarios/')

for scenario in scenarios:
    print 'Building Scenario ' + scenario['id']
    print 'Switching edgetypes and ch.py'

    os.system('cp ' + bikesy_base + '/core/edgetypes' + scenario['edgetypes'] + '.c ' + bikesy_base + '/core/edgetypes.c')
    os.system('cp ' + bikesy_base + '/misc/tripplanner/ch' + scenario['ch'] + '.py ' + bikesy_base + '/misc/tripplanner/ch.py')

    os.system('cd ' + bikesy_base + '/pygs; python setup.py install')

    os.system('mkdir -p ' + settings['basename'] + '/scenarios/' + scenario['id'])
    os.system('cd ' + settings['basename'] + '/scenarios/' + scenario['id'])

    print 'Running gs_compile_gdb with edge weights'

    osm_weight_string = ''
    for linktype, values in scenario['osm_weights'].iteritems():
        for value in values:
            osm_weight_string += ' -' + linktype + ' "' + value + '"'

    os.system('python ' + bikesy_base + '/pygs/graphserver/compiler/compile_graph.py -o ' + settings['basename'] + '/' + settings['filename'] + '.osmdb -p ' + settings['basename'] + '/' + settings['filename'] + '.profiledb ' + osm_weight_string + ' ' + settings['basename'] + '/' + settings['filename'] + '.gdb')

    print 'Run ch.py'
    os.system('python ' + bikesy_base + '/misc/tripplanner/ch.py ./' + settings['filename'])

    print 'Run shortcut_cache.py'
    os.system('python ' + bikesy_base + '/misc/tripplanner/shortcut_cache.py ./' + settings['filename'])

    print 'Copy to scenario folder'
    os.system('cp bayarea.* ' + settings['basename'] + '/scenarios/' + scenario['id'])
