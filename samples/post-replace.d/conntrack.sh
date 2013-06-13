#!/bin/sh 

# Warning! This script should be placed in the
# /etc/netgwm/post-replace.d/ directory to work.
#
# All the scripts placed in post-replace.d are
# executed every time NetGWM changes the current
# network gateway. In these scripts, you can use
# the following arguments:
#
# $1 - new gateway identifier
# $2 - new gateway IP or NaN
# $3 - new gateway device or NaN
# $4 - old gateway identifier or NaN
# $5 - old gateway IP or NaN
# $6 - old gateway device or NaN

onntrack -D -p udp
