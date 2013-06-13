#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#       NetGWM (Network Gateway Manager) is a tool for
#       automatically switching gateways when Internet
#       goes offline.
#       Home page: http://flant.ru/projects/netgwm
#
#       Copyright (C) 2012-2013 CJSC Flant (www.flant.ru)
#       Written by Andrey Polovov <andrey.polovov@flant.ru>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import sys, os, stat
import yaml
import time
import socket
import optparse
import re
import logging

configfile  = '/etc/netgwm/netgwm.yml'
logfile     = '/var/log/netgwm.log'
gwstorefile = '/var/run/netgwm/gwstore.yml'
modefile    = '/var/lib/netgwm/mode'

logging.basicConfig(format = '%(asctime)s %(message)s', filename = logfile, level = logging.INFO)

def main():
    parser = optparse.OptionParser(add_help_option = False, epilog = 'Home page: http://flant.ru/projects/netgwm')
    parser.add_option('-h', '--help', action = 'help', help = 'display this help and exit')
    parser.add_option('-c', '--config', default = configfile, help = 'full path to NetGWM configuration file')
    options, args = parser.parse_args()

    if not os.path.isfile(options.config):
      parser.error('Config file (%s) not found.' % options.config)

    config = yaml.load(open(options.config, 'r'))
    if not os.path.exists('/var/run/netgwm/'): os.mkdir('/var/run/netgwm/')

    try:    gwstore = yaml.load(open(gwstorefile, 'r'))
    except: gwstore = {}

    gateways = []
    if 'gateways' in config and not config['gateways'] is None:
      for gw_identifier, gw_data in config['gateways'].iteritems():
          gateways.append(GatewayManager(gwstore, identifier=gw_identifier, **gw_data))

    currentgw = GatewayManager.get_current_gateway(gateways)

    try:
        if 'mode' in config: mode = config['mode']
        else:                mode = open(modefile, 'r').read().strip()
        if mode not in config['gateways']: raise Exception()
    except: mode = 'auto'

    if mode == 'auto':
        if currentgw is not None and currentgw.check(config['check_sites']):
            # If Internet is available...
            # Looking for a gateway with a higher priority (than current one)
            candidates = [x for x in gateways if x.priority < currentgw.priority]
            for gw in sorted(candidates, key = lambda x: x.priority):
                if gw.check(config['check_sites']) and gw.wakeuptime < (time.time() - config['min_uptime']):
                    # This router works and is stable enough
                    gw.setdefault()
                    post_replace_trigger(newgw=gw, oldgw=currentgw)
                    break
                else: continue
        else:
            # Switching to a gateway having highest priority
            for gw in sorted(gateways, key = lambda x: x.priority):
                if gw == currentgw: continue # For sure, our current gateway doesn't work
                if gw.check(config['check_sites']):
                    gw.setdefault()
                    post_replace_trigger(newgw=gw, oldgw=currentgw)
                    break
                else: continue
            # What a pity! No gateway works :(
    else:
        fixedgw = [x for x in gateways if x.identifier == mode].pop()
        if currentgw is None or currentgw != fixedgw:
            fixedgw.setdefault()
            post_replace_trigger(newgw=fixedgw, oldgw=currentgw)

    if 'check_all_gateways' in config and config['check_all_gateways'] is True:
        for gw in [x for x in gateways if not x.is_checked]: gw.check(config['check_sites'])

    GatewayManager.store_gateways(gateways)


def post_replace_trigger(newgw, oldgw):
    # post-replace.d
    args = []
    args.append(newgw.identifier)
    args.append(newgw.ip  if hasattr(newgw, 'ip')  else 'NaN')
    args.append(newgw.dev if hasattr(newgw, 'dev') else 'NaN')
    args.append(oldgw.identifier if not oldgw is None else 'Nan')
    args.append(oldgw.ip         if not oldgw is None and hasattr(oldgw, 'ip')  else 'NaN')
    args.append(oldgw.dev        if not oldgw is None and hasattr(oldgw, 'dev') else 'NaN')
    for filename in sorted(os.listdir('/etc/netgwm/post-replace.d/')):
        execpath = '/etc/netgwm/post-replace.d/'+filename
        if os.path.isfile(execpath) and (os.stat(execpath).st_mode & stat.S_IXUSR):
            os.system(execpath+' '+' '.join(args))


class GatewayManager:
    def __init__(self, gwstore, **kwargs):
        self.priority   = kwargs['priority']
        self.identifier = kwargs['identifier']
        self.is_checked = False
        if 'ip'  in kwargs and kwargs['ip']  is not None: self.ip  = kwargs['ip']
        if 'dev' in kwargs and kwargs['dev'] is not None: self.dev = kwargs['dev']

        if self.identifier in gwstore: self.wakeuptime = gwstore[self.identifier]['wakeuptime']
        else: self.wakeuptime = 0 # When a gateway appears for the first time, its uptime is set to something BIG

    def __eq__(self, other):
        if other is None: return False
        else:             return self.identifier == other.identifier

    def check(self, check_sites):
        # check gw status
        print 'checking ' + self.identifier
        ipresult = not os.system('/sbin/ip route replace default %s table netgwm_check' % self.generate_route())

        if ipresult is True:
            for site in check_sites:
                try:
                    site_ip = socket.gethostbyname(site)
    
                    os.system('/sbin/ip rule add iif lo to %s lookup netgwm_check' % site_ip)
    
                    p       = os.popen('ping -q -n -W 1 -c 2 %s 2> /dev/null' % site_ip)
                    pingout = p.read()
                    status  = not p.close()
    
                    os.system('/sbin/ip rule del iif lo to %s lookup netgwm_check' % site_ip)
    
                    if status is True:
                        # ping success
                        rtt  = re.search('\d+\.\d+/(\d+\.\d+)/\d+\.\d+/\d+\.\d+', pingout).group(1)
                        info = 'up:'+site+':'+rtt
                        break
                    else:
                        # ping fail
                        info = 'down'

                except:
                    status = False
            
            os.system('/sbin/ip route del default %s table netgwm_check' % self.generate_route())
        else:
            status = False
            info   = 'down'
        
        try: 
            with open('/var/run/netgwm/'+self.identifier, 'w') as f: f.write(info)
        except: pass

        if self.wakeuptime is None and status is True: self.wakeuptime = time.time() # Setting wakeup time if it's not set and server works (has answered to a ping)
        elif status is False:                          self.wakeuptime = None        # Removing wakeup time if server doesn't work (no ping)

        self.is_checked = True

        return status

    def setdefault(self):
        # replace
        print '/sbin/ip route replace default ' + self.generate_route()
        os.system('/sbin/ip route replace default ' + self.generate_route())
        logging.info('route replaced to %s', self.generate_route())

    def generate_route(self):
        res = []
        if hasattr(self, 'ip'):  res.append('via ' + self.ip)
        if hasattr(self, 'dev'): res.append('dev ' + self.dev)
        return ' '.join(res)

    @staticmethod
    def get_current_gateway(gateways):
        currentgw_ip  = os.popen("/sbin/ip route | grep 'default via' | sed -r 's/default via (([0-9]+\.){3}[0-9]+) dev .+/\\1/g'").read().strip()
        currentgw_dev = os.popen("/sbin/ip route | grep 'default dev' | sed -r 's/default dev ([a-z0-9]+)(\s+.*)?/\\1/g'").read().strip()

        if currentgw_ip == '' and currentgw_dev == '': 
            return None
        elif currentgw_ip != '':
            for g in [x for x in gateways if hasattr(x, 'ip')]:
                if g.ip == currentgw_ip: return g 
        elif currentgw_dev != '':
            for g in [x for x in gateways if hasattr(x, 'dev')]:
                if g.dev == currentgw_dev: return g 
        else: raise Exception('current gw is not listed in config.')
        
    @staticmethod
    def store_gateways(gateways):
        gwstore = {}
        for gw in gateways: gwstore[gw.identifier] = {'wakeuptime': gw.wakeuptime}
        open(gwstorefile, 'w').write(yaml.dump(gwstore))

 
if __name__ == '__main__':
    main()
