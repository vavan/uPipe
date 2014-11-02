#!/usr/bin/python

import socket
import sys
import time, datetime
import logging
import argparse
import subprocess

def log(msg):
    logging.info(msg)


class Timer:
    def __init__(self, seconds):
        self.timeout = seconds
        self.before = datetime.datetime.now()
    def expired(self):
        now = datetime.datetime.now()
        return (now - self.before).seconds > self.timeout

class Socket:
    BUFFER_SIZE = 4096
    TIMEOUT = 1
    @staticmethod 
    def to_addr(addr):
        addr = addr.split(':')
        addr[1] = int(addr[1])
        return tuple(addr)
    def __init__(self, local_addr):
        self.local_addr = Socket.to_addr(local_addr)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(self.local_addr)
        self.s.settimeout(Socket.TIMEOUT)
    def receive(self):
        return self.s.recvfrom(Socket.BUFFER_SIZE)
    def reply(self, addr, request):
        self.s.sendto(request, addr)
    def ask(self, addr, request, response = None):
        timer = Timer(seconds = 30)
        while not timer.expired():
            try:
                log('Ask %s -> %s'%(request, addr))
                self.s.sendto(request, addr)
                actual, addr = self.s.recvfrom(Socket.BUFFER_SIZE)
                if (actual == response or response == None):
                    return actual, addr
            except socket.timeout:
                pass
        return '', None
    def ping(self, addr, request, response):
        data = ''
        self.s.sendto(request, addr)
        timer = Timer(seconds = 25)
        while not timer.expired():
            try:
                data, addr = self.s.recvfrom(Socket.BUFFER_SIZE)
            except socket.timeout:
                pass
            if data != response:
                break
        return data
                            

def setup_log(filename):
    if filename == 'stdout':
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    elif filename:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s',filename=filename,filemode='a')
    else:
        logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(message)s')

