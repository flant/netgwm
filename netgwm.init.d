#! /bin/sh
### BEGIN INIT INFO
# Provides:          netgwm
# Required-Start:    $syslog
# Required-Stop:     $syslog
# Should-Start:      $network
# Should-Stop:       $network
# X-Start-Before:    network
# X-Stop-After:      network
# Default-Start:     2 3 4 5
# Default-Stop:      1
# Short-Description: runs script for wan failover
### END INIT INFO

PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
DAEMON=/usr/sbin/netgwm
NAME=netgwm
PIDFILE=/var/run/$NAME.pid
DESC="wan failover service"
START=no
DEFAULT_CONFIG=/etc/default/netgwm

unset TMPDIR

test -x $DAEMON || exit 0

. /lib/lsb/init-functions

. $DEFAULT_CONFIG

# Get the timezone set.
if [ -z "$TZ" -a -e /etc/timezone ]; then
    TZ=`cat /etc/timezone`
    export TZ
fi

case "$1" in
  start)
	log_begin_msg "Starting $DESC: $NAME"
	case "$START" in
	"YES"|"Yes"|"yes"|"True"|"TRUE"|"true") 
		start-stop-daemon --start -b --quiet --pidfile "$PIDFILE" --exec "$DAEMON" && success=1
		log_end_msg $?
		;;
	*)
		echo ""
		echo "netgwm not configured to start, see \$START in $DEFAULT_CONFIG"
		;;
	esac
	;;
  stop)
	log_begin_msg "Stopping $DESC: $NAME"
	start-stop-daemon --stop --quiet --retry 5 --signal 15 --pidfile $PIDFILE --name $NAME && success=1
	rm $PIDFILE
	log_end_msg $?
	;;
  reload|force-reload)
        echo "Error: argument '$1' not supported" >&2
        exit 3
       ;;
  restart)
        echo "Error: argument '$1' not supported" >&2
        exit 3
	;;
  status)
	echo -n "Status of $DESC: "
	if [ ! -r "$PIDFILE" ]; then
		echo "$NAME is not running."
		exit 3
	fi
	if read pid < "$PIDFILE" && ps -p "$pid" > /dev/null 2>&1; then
		echo "$NAME is running."
		exit 0
	else
		echo "$NAME is not running but $PIDFILE exists."
		exit 1
	fi
	;;
  *)
	N=/etc/init.d/${0##*/}
	echo "Usage: $N {start|stop|status}" >&2
	exit 1
	;;
esac

exit 0

