#!/usr/bin/python

import sys, time
import argparse
import subprocess
import socket
import asyncore
from tool import log, setup_log, Timer, to_addr                         


class GirlDiscovery(asyncore.dispatcher):
#TODO hanlde timeouts
    def __init__(self, args):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.bind(to_addr(args.local))      
        self.cupid_addr = to_addr(args.cupid)
        self.name = args.name
        log( 'Start girl at %s. Cupid at: %s'%(args.local, self.cupid_addr) )
        self.sendto('upipe.girl.ready.%s'%self.name, self.cupid_addr)
    def handle_read(self):
        data, addr = self.recvfrom(8192)
        if data:
            log("GOT: %s"%data)
            if data.startswith('upipe.love.'):
                self.peer_addr = to_addr(data[len('upipe.love.'):])
                self.sendto('upipe.hello', self.peer_addr)
                log("Hello to: %s"%(self.peer_addr,))
            elif data.startswith('upipe.hello.done'):
                self.peer_addr = addr
                self.established(self.peer_addr)
            elif data.startswith('upipe.hello'):
                self.peer_addr = addr
                self.sendto('upipe.hello.done', self.peer_addr)
                log("Hello.done to: %s"%(self.peer_addr,))
                self.established(self.peer_addr)
    def established(self, addr):
        log("Established!")
        subprocess.call('killall -9 openvpn', shell = True)
        time.sleep(0.5)
        subprocess.call('openvpn --config girl.ovpn', shell = True)
    

class GirlControl(asyncore.dispatcher_with_send):
#TODO: handle lost of connection
    def __init__(self, args):
        asyncore.dispatcher_with_send.__init__(self)
        self.args = args
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect(to_addr(args.cupid))
        self.send('upipe.register.%s'%args.name)
        log( 'Register girl %s. Cupid at: %s'%(args.name, args.cupid) )
    def handle_read(self):
        data = self.recv(8192)
        if data and data.startswith('upipe.cupid.invite'):
            GirlDiscovery(self.args)             

        
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', dest = 'cupid', type=str, default='54.191.93.115:3478', help='Address of Cupid server (ip:port)')
    parser.add_argument('-l', dest = 'local', type=str, default='0.0.0.0:6000', help='Local address, default 0.0.0.0:6000')
    parser.add_argument('-log', type=str, default='', help='Log file name. Can be stdout. Quiet mode if not specified')
    parser.add_argument('name', type=str, default='', help='Well known NAME of the Girl.')
    return parser.parse_args()

     
def main():
    args = parse_arguments()
    setup_log(args.log)

    c = GirlControl(args)
    asyncore.loop()

main()


