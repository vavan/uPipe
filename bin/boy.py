#!/usr/bin/python

import sys
import argparse
import subprocess
import socket
import asyncore
from tool import log, setup_log, Timer, to_addr  


class Boy(asyncore.dispatcher):

    def __init__(self, args):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.bind(to_addr(args.local))      
        self.cupid = to_addr(args.cupid)
        self.name = args.name
        log( 'Start boy at %s. Cupid at: %s'%(args.local, args.cupid) )
        self.sendto('upipe.boy.invite.%s'%self.name, self.cupid)
        log('Invitation sent')
        
    def handle_read(self):
        data, addr = self.recvfrom(8192)
        if data:
            log("GOT: %s"%data)
            if data.startswith('unknown'):
                sys.exit("ERROR. Unkown name '%s'"%self.name)
            elif data.startswith('upipe.love.'):
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

    def established(self, peer_addr):
        log("Established connection with %s"%(peer_addr,))
        self.close()

      
        
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

    subprocess.call('killall -9 openvpn', shell = True)

    b = Boy(args)
    asyncore.loop()

    openvpn = 'openvpn --config boy.ovpn --remote %s %s'%b.peer_addr
    if args.log:
        openvpn += ' --verb 4'
        if args.log != 'stdout':
            openvpn += ' --log vpn_%s'%args.log
    subprocess.call(openvpn.split())
    #time.sleep(0.2)
    print "DONE!"    

main()


