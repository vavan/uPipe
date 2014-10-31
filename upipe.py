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
            self.reply(to_addr, 'upipe.connect.%s:%s'%from_addr)
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

                log('Received from %s. First 30 bytes: %s'%(addr, data[:30]))

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

class Lover(Socket):
    def __init__(self, local_addr, cupid_addr, name):
        Socket.__init__(self, local_addr)
        self.cupid_addr = Socket.to_addr(cupid_addr)
        self.name = name
    def establish(self, peer_addr):
        timer = Timer(seconds = 60)
        while not timer.expired():
            log('Send hello to %s:%s'%peer_addr)
            replay, addr = self.ask(peer_addr, 'upipe.hello')
            if addr and (addr[0] == peer_addr[0]):
                if replay != 'upipe.hello.done':
                    self.ask(addr, 'upipe.hello.done', 'upipe.hello.done')
                else:
                    self.reply(addr, 'upipe.hello.done')
                log('In love with %s'%str(addr))
                return addr
            log("Couldn't establish")
            return None
    def run(self):
        pass

class Girl(Lover):
    def __init__(self, local_addr, cupid_addr, name):
        Lover.__init__(self, local_addr, cupid_addr, name)
        log( 'Start girl at %s. Cupid at: %s'%(local_addr, self.cupid_addr) )
        self.register()
    def register(self):
        self.ask(self.cupid_addr, 'upipe.register.%s'%self.name, 'upipe.ok')
        log('Registered')
    def run(self):
        while True:
            data = self.ping(self.cupid_addr, '.', '!')
            if data.startswith('upipe.connect.'):
                data = data[len('upipe.connect.'):]
                peer_addr = Socket.to_addr(data)
                self.reply(self.cupid_addr, 'upipe.ok')
                addr = self.establish(peer_addr)
                if addr:
                    return addr
        
class Boy(Lover):
    def __init__(self, local_addr, cupid_addr, name):
        Lover.__init__(self, local_addr, cupid_addr, name)
        log( 'Start boy at %s. Cupid at: %s'%(local_addr, self.cupid_addr) )
    def invite(self):
        log('Invite %s'%self.name)
        peer_addr, addr = self.ask(self.cupid_addr, 'upipe.invite.%s'%self.name)
        log('Resolved invitation: %s'%peer_addr)
        return peer_addr
    def run(self):
        timer = Timer(seconds = 60)
        while not timer.expired():
            peer_addr = self.invite()
            if peer_addr == None:
                log('No response on invitation')
            elif peer_addr == 'unknown':
                sys.exit("ERROR. Unkown name '%s'"%self.name)
            else:
                peer_addr = Socket.to_addr(peer_addr)
                established = self.establish(peer_addr)
                if established:
                    return established
        return None
    
        
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', dest = 'mode', choices=('cupid', 'girl', 'boy'), 
        help='Mode of operation. Cupid - meeting point server. '+
              'Girl - expecting client. '+
              'Boy - initiating client.')
    parser.add_argument('-c', dest = 'cupid', type=str, default='54.191.93.115:3478', help='Address of Cupid server (ip:port)')
    parser.add_argument('-l', dest = 'local', type=str, default='0.0.0.0:6000', help='Local address, default 0.0.0.0:6000')
    parser.add_argument('-log', type=str, default='', help='Log file, print log on screen if not specified')
    parser.add_argument('name', type=str, default='', help='Well known NAME of the Girl.')
    return parser.parse_args()

def setup_log(filename):
    if filename == 'stdout':
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s')
    elif filename:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(message)s',filename=filename,filemode='a')
    else:
        logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(message)s')
    
      
def main():
    args = parse_arguments()
    setup_log(args.log)

    if args.mode == 'cupid':
        Cupid(args.local).start()
    else:
        if args.mode == 'girl':
            while True:
                addr = Girl(args.local, args.cupid, args.name).run()
                subprocess.call('openvpn --remote %s %s --config girl.ovpn'%addr, shell = True)
        elif args.mode == 'boy':
            addr = Boy(args.local, args.cupid, args.name).run()
            subprocess.call('openvpn --config boy.ovpn', shell = True)

main()


