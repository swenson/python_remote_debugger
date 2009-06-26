#!/usr/bin/env python

"""
A remote debugging protocol and server for Python.
This code is meant to be easily integrated into existing code
simply by running start_remote_debugger().

Currently only supports one connection at a time, to avoid creating
too many threads.


Author: Christopher Swenson (chris@caswenson.com)
Homepage: http://github.com/swenson/python_remote_debugger


License: MIT Public License
Copyright (c) 2009 Christopher Swenson

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import cPickle as pickle
import threading
import traceback
import sys
import os
import time
import socket
import struct

try:
  import ssl
except:
  print("SSL is unavailable on this system.")
  ssl = None


MAX_SIZE = 1024 


class RDBConnection(object):  
  def __init__(self, s):
    """Encapsulates a simple Python remote debugging protocol.

    message = length bytes

    where length is a 64-bit unsigned int sent in network (big-endian) order."""
    self.socket = s 

  def recv_msg(self):
    """Receive, unpickle, and return a message from the wire, which should be an array"""
    length_str = self.socket.recv(8)
    length = struct.unpack('!Q', length_str)[0]
    left = length
    data = ''
    while left > 0:
      recv = self.socket.recv(min(MAX_SIZE, left))
      if recv:
        data += recv
        left -= len(recv)
      else:
        break
    return pickle.loads(data)

  def send_msg(self, *args):
    """Send a message constructed from the arguments (sent as a pickled array)"""
    
    message = args
    m = pickle.dumps(message)
    self.socket.sendall(struct.pack('!Q', len(m)))
    self.socket.sendall(m)


class RDBServer(RDBConnection):
  def __init__(self, s, access_code):
    """Start up the standard server for the Python remote debugger.  It inherets
    from the standard protocol, but starts every conversation like this:
    
    Client -> Server: Version (64-bit int, currently 1)
    Client -> Server: Length Passcode (64-bit int length of passcode, followed by passcode)
    """
    
    RDBConnection.__init__(self, s)
    
    # unpack a 64-bit version
    version_str = ''
    while len(version_str) < 8:
      version_str += self.socket.recv(8 - len(version_str))
    version = struct.unpack('!Q', version_str)[0]
    if version != 1:
      self.socket.close()
    
    # unpack a 64-bit length of the pass code
    length_str = ''
    while len(length_str) < 8:
      length_str += self.socket.recv(8 - len(length_str))
    length = struct.unpack('!Q', length_str)[0]
    
    # verify the access code
    check_code = ''
    left = length
    while left > 0:
      data = self.socket.recv(min(MAX_SIZE, left))
      if data:
        check_code += data
        left -= len(data)
      else:
        break
    
    if check_code != access_code:
      self.socket.close()


class RDBClient(RDBConnection):
  def __init__(self, hostname, port, access_code, use_ssl=False):
    """Initiate a client connection to a Python remote debugger.
    
    The looks like:
    
    Client -> Server: Version (64-bit int, currently 1)
    Client -> Server: Length Passcode (64-bit int length of passcode, followed by passcode)    
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if ssl and use_ssl:
      s = ssl.wrap_socket(s)
      
    s.connect((hostname, port))
    RDBConnection.__init__(self, s)
    self.socket.sendall(struct.pack('!QQ', 1, len(access_code)))
    self.socket.sendall(access_code)


def start_remote_debugger(port=1235, passcode="abc", verbose=False):
  """Starts up a remote debuggin server"""
  
  t = threading.Thread(target=remote_debugging_loop, args=(port,passcode))
  t.daemon = True
  t.start()
  if verbose: print("Remote debugger thread started on port " + str(port))


def execute(l):
  """Given a command from the client, execute it and return results."""
  
  command = l[0]
  ret = None
  if command == 'get_thread_list':
    ret = []
    # get all running threads
    for t in threading.enumerate():
      # only return values for threads that have started
      if t.ident:
        ret.append(t.ident)
      
  elif command == 'get_frame':
    id = l[1]
    ret = sys._current_frames()[id]

  elif command == 'get_stack':
    id = l[1]
    ret = traceback.format_stack(sys._current_frames()[id])
    
  elif command == 'get_locals':
    id = l[1]
    locals = sys._current_frames()[id].f_locals
    ret = []
    for k, v in locals.iteritems():
      ret.append((k, str(v)))
      
  elif command == 'get_globals':
    id = l[1]
    locals = sys._current_frames()[id].f_globals
    ret = []
    for k, v in locals.iteritems():
      ret.append((k, str(v)))
      
  elif command == 'execute':
    cmd = l[1]
    # execute within a thread's scope
    if len(l) == 3:
      exec cmd in sys._current_frames()[l[2]].f_globals, sys._current_frames()[l[2]].f_locals
  else:
    raise NameError('"' + str(cmd) + '" is not a valid command')
  
  return ret

def remote_debugging_loop(port=1235, passcode="abc", verbose=False, use_ssl=False, certfile=None, keyfile=None):
  """A loop that runs that listens for connections and creates
  RDBServer objects to serve them."""
  
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.bind(('', port))
  s.listen(1)
  
  if ssl and use_ssl:
    s = ssl.wrap_socket(s, server_side=True, certfile=certfile, keyfile=keyfile)
    
  try:
    while True:
      if verbose: print("Waiting for a connection")
      conn, addr = s.accept()
      if verbose: print("Connection received from " + str(addr))
      r = RDBServer(conn, passcode)
      try:
        while True:
          msg = r.recv_msg()
          r.send_msg(execute(msg))
      except:
        pass
      finally:
        conn.close()
  finally:
    s.close()



if __name__ == '__main__':
  def test_loop():
    """Simple loop to run in background so that the default thread view is interesting."""
    
    var = 123
    while True:
      time.sleep(var)

  port = 1235
  passcode = "abc"

  try:
    if len(sys.argv) > 1:
      port = int(sys.argv[1])
      if len(sys.argv) > 2:
        passcode = sys.argv[2]
  except:
    print "Usage: ./rdb.py [port [passcode]]"
    sys.exit(0)

  start_remote_debugger(port=port, passcode=passcode, verbose=True)

  other_thread = threading.Thread(target=test_loop)
  other_thread.daemon = True
  other_thread.start()
  while True:
    time.sleep(1)

