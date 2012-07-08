#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, stat
import yaml
import time
import socket
import optparse

configfile  = '/etc/gwm/gwm.yml'
gwstorefile = '/tmp/gwm_gwstore.yml'

def main():
    parser = optparse.OptionParser(add_help_option = False)
    parser.add_option('-h', '--help', action = 'help')
    parser.add_option('-c', '--config', default = configfile)
    options, args = parser.parse_args()
    config  = yaml.load(open(options.config, 'r'))

    gwstore = {}
    try: gwstore = yaml.load(open(gwstorefile, 'r'))
    except: pass

    gateways = []
    for gwdesc in config['gateways']:
        gateways.append(GatewayManager(gwdesc, gwstore))

    currentgw = GatewayManager.get_current_gateway(gateways)

    if currentgw is not None and currentgw.check(config['check_sites']):
        # если доступен интернет
        # ищем доступный роутер с приоритетом выше, чем у текущего
        candidates = [x for x in gateways if x.priority < currentgw.priority]
        for gw in sorted(candidates, key = lambda x: x.priority):
            if gw.check(config['check_sites']) and gw.wakeuptime < (time.time() - config['min_uptime']):
                # роутер работает и работает без сбоев достаточно долго
                gw.setdefault()
                break
            else: continue
    else:
        # Срочно переключаемся на самый приоритетный доступный шлюз
        for gw in sorted(gateways, key = lambda x: x.priority):
            if gw == currentgw: continue # и так понятно, что текущий роутер не работает
            if gw.check(config['check_sites']):
                gw.setdefault()
                break
            else: continue
        # ни один роутер не работает

    GatewayManager.store_gateways(gateways)


class GatewayManager:
    def __init__(self, gwdesc, gwstore):
        self.priority = gwdesc['priority']
        if 'ip'  in gwdesc and gwdesc['ip']  is not None: self.ip  = gwdesc['ip']
        if 'dev' in gwdesc and gwdesc['dev'] is not None: self.dev = gwdesc['dev']

        if   hasattr(self, 'ip'):  self.storekey = self.ip
        elif hasattr(self, 'dev'): self.storekey = self.dev

        if hasattr(self, 'storekey') and self.storekey in gwstore: self.wakeuptime = gwstore[self.storekey]['wakeuptime']
        else: self.wakeuptime = 0 # считаем, что при первом появлении роутера в системе, его аптайм -- много лет.

    def __eq__(self, other):
        if hasattr(self, 'ip') and hasattr(self, 'dev') and hasattr(other, 'ip') and hasattr(other, 'dev'):
            return self.ip == other.ip and self.dev == other.dev
        elif hasattr(self, 'ip') and not hasattr(self, 'dev') and hasattr(other, 'ip') and not hasattr(other, 'dev'):
            return self.ip == other.ip
        elif not hasattr(self, 'ip') and hasattr(self, 'dev') and not hasattr(other, 'ip') and hasattr(other, 'dev'):
            return self.dev == other.dev
        else:
            return False

    def check(self, check_sites):
        # check gw status
        print 'checking ' + self.storekey
        os.system('/sbin/ip route replace default %s table gwm_check' % self.generate_route())

        for site in check_sites:
            site_ip = socket.gethostbyname(site)
            os.system('/sbin/ip rule add iif lo to %s lookup gwm_check' % site_ip)
            pingresult = os.system('ping -q -n -W 1 -c 2 %s 1> /dev/null 2>&1' % site_ip)
            os.system('/sbin/ip rule del iif lo to %s lookup gwm_check' % site_ip)
            if not pingresult: break

        if self.wakeuptime is None and not pingresult: self.wakeuptime = time.time() # Если не установлено время подъема и сервак пинганулся -- устанавливае
        elif pingresult:                               self.wakeuptime = None           # Если не пинганулся -- затираем

        os.system('/sbin/ip route del default %s table gwm_check' % self.generate_route())
        return not pingresult

    def setdefault(self):
        # replace
        print '/sbin/ip route replace default ' + self.generate_route()
        os.system('/sbin/ip route replace default ' + self.generate_route())

        # post-replace.d
        arg = self.ip if hasattr(self, 'ip') else self.dev if hasattr(self, 'dev') else 'unknown'
        for filename in sorted(os.listdir('/etc/gwm/post-replace.d/')):
            execpath = '/etc/gwm/post-replace.d/'+filename
            if os.path.isfile(execpath) and (os.stat(execpath).st_mode & stat.S_IXUSR):
                os.system(execpath+' '+arg)

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
        for gw in gateways: gwstore[gw.storekey] = {'wakeuptime': gw.wakeuptime}
        open(gwstorefile, 'w').write(yaml.dump(gwstore))

 
if __name__ == '__main__':
    main()

