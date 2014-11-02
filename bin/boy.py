#!/usr/bin/python

import sys
import argparse
import subprocess
from tool import log, setup_log, Timer, Socket


class Boy(Socket):

    def __init__(self, local_addr, cupid_addr, name):
        Socket.__init__(self, local_addr)
        self.cupid_addr = Socket.to_addr(cupid_addr)
        self.name = name
        log( 'Start boy at %s. Cupid at: %s'%(local_addr, self.cupid_addr) )

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
    parser.add_argument('-c', dest = 'cupid', type=str, default='54.191.93.115:3478', help='Address of Cupid server (ip:port)')
    parser.add_argument('-l', dest = 'local', type=str, default='0.0.0.0:6000', help='Local address, default 0.0.0.0:6000')
    parser.add_argument('-log', type=str, default='', help='Log file name. Can be stdout. Quiet mode if not specified')
    parser.add_argument('name', type=str, default='', help='Well known NAME of the Girl.')
    return parser.parse_args()

    
      
def main():
    args = parse_arguments()
    setup_log(args.log)

    addr = Boy(args.local, args.cupid, args.name).run()
    subprocess.call('openvpn --remote %s %s --config boy.ovpn'%addr, shell = True)

main()


