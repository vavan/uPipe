#!/usr/bin/python

import socket
import sys
import time
import logging
import argparse

def log(msg):
    logging.info(msg)

class Socket:
    BUFFER_SIZE = 4096
    @staticmethod 
    def to_addr(addr):
        if type(addr) == str:
            addr = addr.split(':')
        addr[1] = int(addr[1])
        return tuple(addr)
    def __init__(self, local_addr):
        self.local_addr = local_addr
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(Socket.to_addr(local_addr))
    def sendto(self, data, addr):
        self.s.sendto(data, addr)
    def recvfrom(self):
        return self.s.recvfrom(Socket.BUFFER_SIZE)

class Cupid(Socket):
    def __init__(self, local_addr):
        Socket.__init__(self, local_addr)
        self.registered = {}
    def on_register(self, name, addr):
        self.registered[name] = addr
        self.sendto('ok', addr)
        log("Register [%s] = %s"%(name, addr))
    def on_invite(self, name, from_addr):
        if name in self.registered:
            to_addr = self.registered[name]
            log("Request to connect from %s to %s"%(from_addr, to_addr))
            self.sendto("%s:%s"%to_addr, from_addr)
            self.sendto("upipe.connect.%s:%s"%from_addr, to_addr)
        else:
            log("Peer asked for unknown name: %s"%name)
            self.sendto('unknown', from_addr)
    def start(self):
        log('Cupid listen on: %s'%self.local_addr)
        while True:
            try:
                data, addr = self.recvfrom()
                log("Received from %s, %s bytes"%(addr, len(data)))

                if data.startswith('upipe.'):
                    data = data[len('upipe.'):]
                    if data.startswith('register.'):
                        name = data[len('register.'):]
                        self.on_register(name, addr)
                    elif data.startswith('invite.'):
                        name = data[len('invite.'):]
                        self.on_invite(name, addr)
                elif data == '.':
                    self.sendto('!', addr)
            except KeyboardInterrupt:
                break
        self.s.close()
        log("Cupid stopped")
        time.sleep(1)

class LoverImpl(Socket):
    def __init__(self, local_addr, meeting_server_addr):
        Socket.__init__(self, local_addr)
        self.meeting_server_addr = Socket.to_addr(meeting_server_addr)
        log( 'Start client at %s. Meeting at: %s'%(local_addr, self.meeting_server_addr) )
    def register(self, name):
        self.sendto('upipe.register.%s'%name, self.meeting_server_addr)
        data, addr = self.recvfrom()
        log("Registered: %s"%data)
    def invite(self, name):
        log('Invite %s'%name)
        self.sendto('upipe.invite.%s'%name, self.meeting_server_addr)
        data, addr = self.recvfrom()
        peer_addr = Socket.to_addr(addr)
        log("Invited: %s:%s"%peer_addr)
        return peer_addr
    def ping(self):
        #self.s.settimeout(1)
        self.sendto('.', self.meeting_server_addr)
        try:
            data, addr = self.recvfrom()
        except socket.timeout:
            log("timeout")
        else:
            time.sleep(3)
        log("Ping: %s"%data)
        return data
    def establish(self, peer_addr):
        while True:
            log("Send hello to %s:%s"%peer_addr)
            self.sendto('upipe.hello', peer_addr)
            try:
                log("Wait to respo")
                #self.s.settimeout(5)
                data, addr = self.recvfrom()
                #self.s.settimeout(1)
                log("Got resp: %s"%data)
                if addr == peer_addr and data == 'upipe.hello':
                    return True
            except socket.timeout:
                pass
        return False
        
class Lover(LoverImpl):
    def __init__(self, local_addr, meeting_server_addr):
        LoverImpl.__init__(self, local_addr, meeting_server_addr)
        
    def expect(self, name):
        self.register(name)
        while True:
            data = self.ping()
            if data.startswith('upipe.connect.'):
                data = data[len('upipe.connect.'):]
                peer_addr = Socket.to_addr(data)
                if self.establish(peer_addr):
                    self.join(peer_addr)
                    break
                    
    def connect(self, name):
        peer_addr = self.invite(name)
        if peer_addr != 'unknown':
            if self.establish(peer_addr):
                self.join(peer_addr)
                
    def join(self, peer_addr):
        print "Two lovers joined: %s + %s"%(local_addr, peer_addr)
        time.sleep(20)



        
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
    
        
def main():
    args = parse_arguments()
    setup_log(args.log)

    if args.mode == 'cupid':
        Cupid(args.local).start()
    else:
        if args.mode == 'girl':
            girl = Lover(args.local, args.cupid)
            girl.expect(args.name)
        elif args.mode == 'boy':
            boy = Lover(args.local, args.cupid)
            boy.connect(args.name)

main()            