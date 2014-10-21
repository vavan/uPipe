#!/usr/bin/python

import socket
import sys
import threading, time
import ssl
import logging
import subprocess

SOCKET_TIMEOUT = 20

logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(message)s',
#                        filename='ssl-tunel.log',
#                        filemode='a'
                        )


def log(msg):
    logging.error(msg)

BUFFER_SIZE = 4096


class Base:
    def __init__(self, local_addr, mp_addr):
        self.mp_addr = mp_addr
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(local_addr)
        #self.s.settimeout(2)
        log('Start at %s:%s'%local_addr)
    def register(self, name):
        self.s.sendto('upipe.register.%s'%name, self.mp_addr)
        data, addr = self.s.recvfrom(BUFFER_SIZE)
        log("Registered: %s"%data)
    def get(self, name):
        log('upipe.get.%s'%name)
        log(self.mp_addr)
        self.s.sendto('upipe.get.%s'%name, self.mp_addr)
        data, addr = self.s.recvfrom(BUFFER_SIZE)
        peer_addr = data.split(':')
        peer_addr[1] = int(peer_addr[1])
        peer_addr = tuple(peer_addr)
        log("Get: %s:%s"%peer_addr)
        return peer_addr
    def ping(self):
        #self.s.settimeout(1)
        self.s.sendto('.', self.mp_addr)
        try:
            data, addr = self.s.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            log("timeout")
        else:
            time.sleep(3)
        #self.s.settimeout(2)
        log("Ping: %s"%data)
        return data

        
class Client(Base):
    def __init__(self, local_port, addr, args):
        Base.__init__(self, local_port, addr)
        self.args = args
    def establish(self, peer_addr):
        while (1):
            log("Send hello to %s:%s"%peer_addr)
            self.s.sendto('upipe.hello', peer_addr)
            try:
                log("Wait to respo")
                #self.s.settimeout(5)
                data, addr = self.s.recvfrom(BUFFER_SIZE)
                #self.s.settimeout(1)
                log("Got resp: %s"%data)
                if addr == peer_addr and data == 'upipe.hello':
                    return True
            except socket.timeout:
                pass
        return False
    def make_pipe(self):
        log("ESTABLISHED")
        time.sleep(20)
        #child = Popen(self.args, stdin = self.s, stdout = self.s)
    def expect(self):
        while 1:
            data = self.ping()
            if data.startswith('upipe.connect.'):
                data = data[len('upipe.connect.'):]
                peer_addr = data.split(':')
                peer_addr[1] = int(peer_addr[1])
                peer_addr = tuple(peer_addr)
                #self.s.settimeout(1)
                if self.establish(peer_addr):
                    self.make_pipe()
                    break
    def connect(self, name):
        peer_addr = self.get(name)
        if peer_addr != 'unknown':
            if self.establish(peer_addr):
                self.make_pipe()
            


class MeetingPoint:
    def __init__(self, server_url):
        self.ip, self.port = server_url
        self.registered = {}
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind((self.ip, int(self.port)))
    def start(self):
        while 1:
            try:
                data, addr = self.s.recvfrom(BUFFER_SIZE)
                log("Received from %s, %s bytes"%(str(addr), len(data)))

                if data.startswith('upipe.'):
                    data = data[len('upipe.'):]
                    if data.startswith('register.'):
                        data = data[len('register.'):]
                        name = data
                        self.registered[name] = addr
                        self.s.sendto('ok', addr)
                        log("Register [%s] = %s"%(name, addr))
                    elif data.startswith('get.'):
                        data = data[len('get.'):]
                        name = data
                        if name in self.registered:
                            peer_addr = self.registered[name]
                            log("Request: %s:%s"%peer_addr)
                            self.s.sendto("%s:%s"%peer_addr, addr)
                            self.s.sendto("upipe.connect.%s:%s"%addr, peer_addr)
                        else:
                            response = 'unknown'
                            log("Get: %s"%peer_addr)
                            self.s.sendto(response, addr)
                elif data == '.':
                    self.s.sendto('!', addr)
          
            except KeyboardInterrupt:
                break
        self.s.close()
        print("EXIT")
        time.sleep(1)

LOCAL_PORT = 5000

if len(sys.argv) >= 4:
    mode = sys.argv[1]
    name = sys.argv[2]
    addr = sys.argv[3].split(':')
    addr[1] = int(addr[1])
    addr = tuple(addr)

    if mode == 'm':
        l = MeetingPoint(addr)
        l.start()
    else:
        if mode == 's':
            c = Client(('10.1.10.23', 5000), addr, sys.argv[4:])
            c.register(name)
            c.expect()
        elif mode == 'c':
            c = Client(('10.1.10.23', 6000), addr, sys.argv[4:])
            c.connect(name)



else:
    print("USAGE: m|c|s name ip:port")



