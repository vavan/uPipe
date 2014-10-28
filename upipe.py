#!/usr/bin/python

import socket
import sys
import time, datetime
import logging
import argparse

def log(msg):
    logging.info(msg)

class Socket:
    BUFFER_SIZE = 4096
    TIMEOUT = 1
    PING_TIMEOUT = 25
    @staticmethod 
    def to_addr(addr):
        if type(addr) == str:
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
        while True:
            try:
                self.s.sendto(request, addr)
                actual, addr = self.s.recvfrom(Socket.BUFFER_SIZE)
                if (actual == response or response == None):
                    return actual, addr
            except socket.timeout:
                if (response == None):
                    return '', None
    def ping(self, addr, request, response):
        data = ''
        self.s.sendto(request, addr)
        then = datetime.datetime.now()
        while True:
            try:
                data, addr = self.s.recvfrom()
            except socket.timeout:
                pass
            now = datetime.datetime.now()
            if (now - then).seconds >= PING_TIMEOUT:
                break
            if data != response:
                break
        return data
                            

class Cupid(Socket):
    def __init__(self, local_addr):
        Socket.__init__(self, local_addr)
        self.registered = {}
    def on_register(self, name, addr):
        self.registered[name] = addr
        self.reply(addr, 'upipe.ok')
        log('Register [%s] = %s'%(name, addr))
    def on_invite(self, name, from_addr):
        if name in self.registered:
            to_addr = self.registered[name]
            log('Request to connect from %s to %s'%(from_addr, to_addr))
            self.reply(from_addr, '%s:%s'%to_addr)
            self.ask(to_addr, 'upipe.connect.%s:%s'%from_addr, 'upipe.ok')
        else:
            log('Peer asked for unknown name: %s'%name)
            self.reply(from_addr, 'unknown')
    def start(self):
        log('Cupid listen on: %s'%str(self.local_addr))
        while True:
            try:
                self.s.settimeout(None)
                data, addr = self.receive()
                self.s.settimeout(Socket.TIMEOUT)

                log('Received from %s, %s bytes'%(addr, len(data)))

                if data.startswith('upipe.'):
                    data = data[len('upipe.'):]
                    if data.startswith('register.'):
                        name = data[len('register.'):]
                        self.on_register(name, addr)
                    elif data.startswith('invite.'):
                        name = data[len('invite.'):]
                        self.on_invite(name, addr)
                elif data == '.':
                    self.reply(addr, '!')
            except KeyboardInterrupt:
                break
        self.s.close()
        log('Cupid stopped')
        time.sleep(1)

class Lover(Socket):
    def __init__(self, local_addr, cupid_addr, name):
        Socket.__init__(self, local_addr)
        self.cupid_addr = Socket.to_addr(cupid_addr)
        self.name = name
    def establish(self, peer_addr):
        while True:
            log('Send hello to %s:%s'%peer_addr)
            replay, addr = self.ask(peer_addr, 'upipe.hello')
            #IP should be the same, PORT may be different because of symetric NAT
            if addr[0] == peer_addr[0]:
                if replay != 'upipe.hello.done':
                    self.ask(addr, 'upipe.hello.done', 'upipe.hello.done')
                else:
                    self.reply(addr, 'upipe.hello.done')
                return addr
    def run(self):
        pass

class Girl(Lover):
    def __init__(self, local_addr, cupid_addr, name):
        Lover.__init__(self, local_addr, cupid_addr, name)
        log( 'Start girl at %s. Cupid at: %s'%(local_addr, self.cupid_addr) )
    def register(self):
        self.ask(self.cupid_addr, 'upipe.register.%s'%self.name, 'upipe.ok')
        log('Registered')
    def ping(self):
        return self.ping(self.cupid_addr, '.', '!')
    def run(self):
        self.register()
        while True:
            data = self.ping()
            if data.startswith('upipe.connect.'):
                data = data[len('upipe.connect.'):]
                peer_addr = Socket.to_addr(data)
                self.reply(self.cupid_addr, 'upipe.ok')
                return self.establish(peer_addr)
        
class Boy(Lover):
    def __init__(self, local_addr, cupid_addr, name):
        Lover.__init__(self, local_addr, cupid_addr, name)
        log( 'Start boy at %s. Cupid at: %s'%(local_addr, self.cupid_addr) )
    def invite(self):
        log('Invite %s'%self.name)
        peer_addr, addr = self.ask(self.cupid_addr, 'upipe.invite.%s'%self.name)
        peer_addr = Socket.to_addr(peer_addr)
        log('Invited: %s:%s'%peer_addr)
        return peer_addr
    def run(self):
        peer_addr = self.invite(name)
        if peer_addr != 'unknown':
            return self.establish(peer_addr)
    
        
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', dest = 'mode', choices=('cupid', 'girl', 'boy'), 
        help='Mode of operation. Cupid - meeting point server. '+
              'Girl - expecting client. '+
              'Boy - initiating client.')
    parser.add_argument('-c', dest = 'cupid', type=str, default='54.191.93.115:3478', help='Address of Cupid server (ip:port)')
    parser.add_argument('-l', dest = 'local', type=str, default='0.0.0.0:6000', help='Local address, default 0.0.0.0:6000')
    parser.add_argument('-log', type=str, default='', help='Log file, print log on screen if not specified')
    parser.add_argument('name', type=str, default='', help='Well known NAME of he Girl.')
    return parser.parse_args()

def setup_log(filename):
    if filename:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s',filename=filename,filemode='a')
    else:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    
def parse_addrs(addrs):
    parts = addrs.split(',')
    main = parts[0].split(':')
    ip = main[0]
    ports = [main[1]]+parts[1:]
    return map(lambda x: ip+':'+x, ports)
        
def main():
    args = parse_arguments()
    setup_log(args.log)

    if args.mode == 'cupid':
        Cupid(args.local).start()
    else:
        addrs = parse_addrs(args.local)
        if args.mode == 'girl':
            lover = Girl
        elif args.mode == 'boy':
            lover = Boy
        for i, a in enumerate(addrs):
            peer = lover(a, args.cupid, args.name+str(i) )
            print peer.run()

main()            
