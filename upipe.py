#!/usr/bin/python

import socket
import sys
import threading, time
import ssl
import logging
import subprocess

SOCKET_TIMEOUT = 20

#logging.basicConfig(level=logging.DEBUG,
#                        format='%(asctime)s %(message)s',
#                        filename='ssl-tunel.log',
#                        filemode='a'
#                        )


def log(msg):
    logging.error(msg)

BUFFER_SIZE = 4096


class Base:
    def __init__(self, local_port, mp_addr):
        self.mp_addr = mp_addr
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(('0.0.0.0', local_port))
        self.s.settimeout(1)
    def register(self, name):
        self.s.sendto('upipe.register.%s'%name, self.mp_addr)
        data, addr = self.s.recvfrom(BUFFER_SIZE)
        log("Registered: %s"%data)
    def get(self, name):
        self.s.sendto('upipe.get.%s'%name, self.mp_addr)
        data, addr = self.s.recvfrom(BUFFER_SIZE)
        peer_addr = data.split(':')
        log("Get: %s"%peer_addr)
        return peer_addr
    def ping(self):
        self.s.settimeout(25)
        self.s.sendto('.', self.mp_addr)
        try:
            data, addr = self.s.recvfrom(BUFFER_SIZE)
        except socket.tumeout:
            log("timeout")
        log("Ping: %s"%data)
        return data

        
class Client(Base):
    def __init__(self, local_port, addr, args):
        Base.__init__(self, local_port, addr)
        self.args = args
    def establish(self, peer_addr):
        while (1):
            self.s.sendto('upipe.hello', peer_addr)
            data, addr = self.s.recvfrom(BUFFER_SIZE)
            if addr == peer_addr and data == 'upipe.ok':
                return True
        return False
    def make_pipe(self):
        child = Popen(self.args, stdin = self.s, stdout = self.s)
    def expect(self):
        while 1:
            data = self.ping()
            if data.startswith('upipe.connect.'):
                data = data[len('upipe.connect.'):]
                peer_addr = data.split(':')
            if peer_addr:
                self.s.settimeout(1)
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
                            log("Get: %s"%peer_addr)
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
        c = Client(LOCAL_PORT, addr, sys.argv[4:])
        if mode == 's':
            c.register(name)
            c.expect()
        elif mode == 'c':
            c.connect(name)



else:
    print("USAGE: m|c|s name ip:port")



