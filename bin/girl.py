#!/usr/bin/python

import sys
import argparse
import subprocess
from tool import log, setup_log, Timer, Socket                         

class Girl(Socket):
    def __init__(self, local_addr, cupid_addr, name):
        Socket.__init__(self, local_addr)
        self.cupid_addr = Socket.to_addr(cupid_addr)
        self.name = name
        log( 'Start girl at %s. Cupid at: %s'%(local_addr, self.cupid_addr) )
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

    while True:
        girl = Girl(args.local, args.cupid, args.name)
        girl.register()
        girl.run()
        subprocess.call('openvpn --config girl.ovpn', shell = True)

main()


