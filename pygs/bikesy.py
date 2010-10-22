from graphserver.ext.routeserver.routeserver import RouteServer, WalkOptions

def slogger( config, tags):
    print "Yikes"
    return 10

class BikesyServer(RouteServer):

    def __init__(self, *args, **kwargs):
        print "Mooooo"
        RouteServer.__init__(self, *args, **kwargs)
        self.config=kwargs.get('config',{})

    def path(self, 
             origin, 
             dest,
             currtime=None, 
             jsoncallback=None):
        return RouteServer.path(self, 
                         origin, 
                         dest,
                         currtime=currtime, 
                         hill_reluctance=self.config['walk_options_config']['hill_reluctance'],
                         jsoncallback=jsoncallback)


