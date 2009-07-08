"""
Web server module.  Simply run

import rdb

rdb.web_server.start_server()

to start up a remote web server instance.

TODO:
  * Authentication support
"""

import cherrypy
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


def start_server(port=8080, ssl=False, ssl_certificate=None, ssl_private_key=None):
  cherrypy.config.update({'server.socket_port': port,})
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
      
  _t = threading.Thread(name="RDBServerThread", target=cherrypy.quickstart, args=[RDBWebServer()])
  _t.daemon = True
  _t.start()


if __name__ == '__main__':
  start_server()
  
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
