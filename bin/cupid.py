#!/usr/bin/python

import sys
import argparse
import subprocess
import asyncore
import socket
from tool import log, setup_log, to_addr, Timer



class GirlAgent(asyncore.dispatcher_with_send):
    def __init__(self, cupid, sock):
        asyncore.dispatcher_with_send.__init__(self, sock)
        self.cupid = cupid
    def handle_read(self):
        data = self.recv(8192)
        if data and data.startswith('upipe.register.'):
            name = data[len('upipe.register.'):]
            self.cupid.on_register(name, self)
    def handle_close(self):
        self.cupid.on_deregister(self)
    def invite(self, name):
        log('Invitation sent to girl: %s'%name)
        self.send('upipe.cupid.invite')
        
                              
class GirlListener(asyncore.dispatcher):
    def __init__(self, cupid, local_addr):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(to_addr(local_addr))
        self.listen(5)
        self.cupid = cupid
        log('Cupid waiting for girls on: %s'%str(local_addr))
    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            log('Incoming connection from %s' % repr(addr))
            handler = GirlAgent(self.cupid, sock)        

class BoyListener(asyncore.dispatcher):
    def __init__(self, cupid, local_addr):
        asyncore.dispatcher.__init__(self)
        self.cupid = cupid
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.bind(to_addr(local_addr))
        log('Cupid waiting for boys on: %s'%str(local_addr))
    def on_ready(self, name, girl_addr):
        log('Girl is ready: %s'%name)
        self.sendto('upipe.love.%s:%s'%boy_addr, girl_addr)
        boy_addr = self.cupid.interested_boy(name)
        self.sendto('upipe.love.%s:%s'%girl_addr, boy_addr)
    def on_invite(self, name, from_addr):
        if self.cupid.is_known(name):
            self.cupid.invite(name, from_addr)
        else:
            log('Peer asked for unknown name: %s'%name)
            self.sendto('unknown', from_addr)
    def handle_read(self):
        data, addr = self.recvfrom(4096)
        log('Received from %s. First 30 bytes: %s'%(addr, data[:30]))
        if data.startswith('upipe.'):
            data = data[len('upipe.'):]
            if data.startswith('boy.invite.'):
                name = data[len('boy.invite.'):]
                self.on_invite(name, addr)
            elif data.startswith('girl.ready.'):
                name = data[len('girl.ready.'):]
                self.on_ready(name, addr)

    
class Girl:
    def __init__(self, agent):
        self.control = agent
        self.meeting = None
        self.boy = None

          
class Cupid:
    def __init__(self):
        self.registered = {}
    def on_register(self, name, agent):
        self.registered[name] = Girl(agent)
        log('Registered: %s'%name)
    def on_deregister(self, agent):
        for name, i in self.registered.iteritems():
            if agent == i:
                log('UnRegistered: %s'%name)
                del self.registered[name]
                break
    def is_known(self, name):
        return name in self.registered
    def invite(self, name, addr):
        log('Boy [%s] is asked for girl [%s]'%(addr, name))
        self.registered[name].boy = addr
        self.registered[name].control.invite()
    def interested_boy(self, name, addr):
        return self.registered[name].boy
        
        
    
        
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', dest = 'cupid', type=str, default='0.0.0.0:3478', help='Local address for Cupid (tcp & udp), default 0.0.0.0:3478')
    parser.add_argument('-log', type=str, default='', help='Log file name. Can be stdout. Quiet mode if not specified')
    return parser.parse_args()

    
      
def main():
    args = parse_arguments()
    setup_log(args.log)

    c = Cupid()
    g = GirlListener(c, args.cupid)
    b = BoyListener(c, args.cupid) 
    asyncore.loop()

main()


