#!/usr/bin/python

import sys
import argparse
import subprocess
from tool import log, setup_log, Timer, Socket                         

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

    
        
def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', dest = 'local', type=str, default='0.0.0.0:6000', help='Local address, default 0.0.0.0:6000')
    parser.add_argument('-log', type=str, default='', help='Log file name. Can be stdout. Quiet mode if not specified')
    return parser.parse_args()

    
      
def main():
    args = parse_arguments()
    setup_log(args.log)

    Cupid(args.local).start()

main()


