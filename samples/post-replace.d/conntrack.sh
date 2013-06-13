#!/bin/sh 

# Warning! This script should be placed in the
# /etc/netgwm/post-replace.d/ directory to work.
#
# With default route changing, TCP connections
# are reset but UDP streams are not. It leads to
# some (UDP related) network services (Asterisk,
# etc) trying to send packages via the outdated
# (not currently working) gateway.

conntrack -D -p udp
