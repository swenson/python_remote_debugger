"""
Web server module.  Simply run

import rdb

rdb.web_server.start_server()

to start up a remote web server instance.
"""

import cherrypy
# cherrypy 3.2+
# import cherrypy.lib.auth_basic
import jinja2
import threading
import sys
import traceback
import socket
import os
import os.path
import time

_env = jinja2.Environment(loader=jinja2.PackageLoader('rdb', 'templates'), autoescape=True) 

class RDBWebServer(object):
  @cherrypy.expose
  @cherrypy.tools.encode(encoding='UTF-8') 
  def index(self):
    threads = []
    # get all running threads
    for t in threading.enumerate():
      # only return values for threads that have started
      if t.ident:
        threads.append(t)
    
    rdb_threads = [t for t in threads if t.name.startswith("_TimeoutMonitor") or \
                    t.name.startswith("CP WSGIServer Thread") or \
                    t.name.startswith("HTTPServer Thread") or \
                    t.name.startswith("Autoreloader") or \
                    t.name.startswith("RDBServerThread")]
                    
    threads = [t for t in threads if t not in rdb_threads]
    t = _env.get_template('index.html')

    modules = sys.modules.keys()
    modules.sort()        
    path = sys.path
    hostname = socket.gethostname()
    arch = os.uname()[-1]
    return t.render(modules=modules, threads=threads, rdb_threads=rdb_threads, path=path, hostname=hostname, arch=arch)

  @cherrypy.expose
  @cherrypy.tools.encode(encoding='UTF-8') 
  def thread(self, id):
    id = int(id)
    print id  
    print sys._current_frames()
    stack = '<br />'.join(traceback.format_stack(sys._current_frames()[id]))
    stack = traceback.format_stack(sys._current_frames()[id])
    locals = sys._current_frames()[id].f_locals
    globals = sys._current_frames()[id].f_globals
    t = _env.get_template('thread.html')

    return t.render(id=id, stack=stack, locals=locals, globals=globals)


def start_server(port=8080,
                 username=None,
                 password=None,
                 ssl=False, ssl_certificate=None, ssl_private_key=None):
  
  # set up the port
  cherrypy.config.update({'server.socket_port': port,})
  
  conf = {}               
  # if a username / password is specified, then use it with basic authentication
  if username and password:
    userpassdict = {username: password}
    
    # save for CherryPy 3.2+
    # checkpassword = cherrypy.lib.auth_basic.checkpassword_dict(userpassdict)
    # basic_auth = {'tools.auth_basic.on': True,
    #               'tools.auth_basic.realm': 'earth',
    #               'tools.auth_basic.checkpassword': checkpassword,
    # }
    
    # password pass-through
    def pass_through(x): return x
    
    basic_auth = {'tools.basic_auth.on': True,
                  'tools.basic_auth.realm': 'pdb',
                  'tools.basic_auth.users': userpassdict,
                  'tools.basic_auth.encrypt': pass_through,
    }
    conf = {'/': basic_auth}
    #cherrypy.config.update({ '/' : basic_auth })
    
  
  # configure SSL support, if asked
  if ssl:
    if ssl_certificate and os.path.exists(ssl_certificate) and \
       ssl_private_key and os.path.exists(ssl_private_key_file):
      cherrypy.config.update({'global': {
        'server.ssl_certificate': ssl_certificate,
        'server.ssl_private_key': ssl_private_key,
      }})
    else:
      print("Bad SSL parameters.  Disabling SSL.")
      ssl = False
  
  # finally, start the thread
  _t = threading.Thread(name="RDBServerThread",
                       target=cherrypy.quickstart,
                       args=[RDBWebServer()],
                       kwargs={'config': conf})
  _t.daemon = True
  _t.start()
  return _t


if __name__ == '__main__':
  import optparse
  
  parser = optparse.OptionParser()
  parser.add_option("-p", "--port", dest="port", default=8080, type="int",
                    help="username for authentication")
  parser.add_option("-u", "--user", dest="username",
                    help="username for authentication")
  parser.add_option("-P", "--password", dest="password",
                    help="password for authentication")
  parser.add_option("-s", "--ssl", dest="ssl", action="store_true",
                    help="Enable SSL")
  parser.add_option("-c", "--cert", dest="ssl_certificate",
                    help="SSL server certificate")
  parser.add_option("-k", "--key", dest="ssl_private_key",
                    help="SSL private key file")
                    
  (options, args) = parser.parse_args()
  
  
  _t = start_server(port=options.port, username=options.username, password=options.password,
                    ssl=options.ssl, ssl_certificate=options.ssl_certificate,
                    ssl_private_key=options.ssl_private_key)
  
  def test_loop():
    """Simple loop to run in background so that the default thread view is interesting."""
    
    var = 123
    while _t.isAlive():
      time.sleep(1)
      
  other_thread = threading.Thread(target=test_loop)
  other_thread.daemon = True
  other_thread.start()
  
  while _t.isAlive():
    time.sleep(1)
