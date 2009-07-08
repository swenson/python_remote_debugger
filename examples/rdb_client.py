#!/usr/bin/env python

"""
A very simple, rather ugly remote debugging client for Python, for viewing the state
of a remote Python process.

Run with ./rdb_client.py [hostname [port [passcode]]]


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

from Tkinter import *
import cPickle as pickle
import threading
import traceback
import sys
import os
import time
import socket  
from rdb import RDBClient


class RDBGui(object):  
  def __init__(self, host="localhost", port=1235, password="abc"):
    """Starts up a simple GUI that can be used to remotely view a Python instance using
    the Python remote debugger protocol in rdb.py"""
    
    self.root = Tk()
    self.client = RDBClient(host, port, password)
    r = 0
    send_button = Button(self.root, text="Refresh thread list", command=self.refresh_thread_list)
    send_button.grid(row=r)
    r += 1
    
    self.thread_list_label = Label(self.root, text="Thread List")
    self.thread_list_label.grid(row=r)
    r += 1
    
    self.thread_list = Listbox(self.root, selectmode=SINGLE)
    #self.thread_list.bind('<Button-1>', self.update_vars)
    self.thread_list.grid(row=r)
    
    
    view_thread_button = Button(self.root, text="View Thread", command=self.update_vars)
    view_thread_button.grid(row=r, column=1)
    r += 1
    
    self.locals_list_label = Label(self.root, text="Local variables")
    self.locals_list_label.grid(row=r)
    r += 1
    
    self.locals_list = Listbox(self.root)
    self.locals_list.grid(row=r)
    r += 1
    
    self.stack_text_label = Label(self.root, text="Stack trace")
    self.stack_text_label.grid(row=r)
    r += 1
    
    self.stack_text = Text(self.root)
    self.stack_text.grid(row=r)
    
    self.refresh_thread_list()

  def update_vars(self, point=None):
    """Update the display to show variables and the stack"""
    
    which = self.thread_list.curselection()
    which = int(which[0])
    id = self.thread_ids[which]
    self.client.send_msg("get_locals", id)
    self.locals = self.client.recv_msg()[0]
    
    self.locals_list.delete(0, END)
    
    for k, v in self.locals:
      self.locals_list.insert(END, str(k) + " = " + str(v))
    
    self.client.send_msg("get_stack", id)
    stack = self.client.recv_msg()[0]
    self.stack_text.delete(1.0, END)
    self.stack_text.insert(END, "".join(stack))    
    
  def refresh_thread_list(self):
    """Update the thread list"""
    
    self.client.send_msg("get_thread_list")
    self.thread_ids = self.client.recv_msg()[0]
    self.thread_list.delete(0, END)
    for id in self.thread_ids:
      self.thread_list.insert(END, str(id))
      
  def run(self):
    self.root.mainloop()


if __name__ == '__main__':
  RDBGui(*sys.argv[1:]).run()

