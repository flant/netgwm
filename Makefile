all: stamp

stamp:
	touch stamp

install:
	install -d $(DESTDIR)/usr/lib/netgwm/
	install -d $(DESTDIR)/var/lib/netgwm/
	install -d $(DESTDIR)/etc/netgwm/
	install -d $(DESTDIR)/etc/init.d/
	install -d $(DESTDIR)/etc/default/
	install -d $(DESTDIR)/usr/sbin/
	cp -r $(CURDIR)/samples/* $(DESTDIR)/etc/netgwm/
	install $(CURDIR)/netgwm.py $(DESTDIR)/usr/lib/netgwm/netgwm.py
	install $(CURDIR)/netgwm.init.d $(DESTDIR)/etc/init.d/netgwm
	install $(CURDIR)/netgwm.default $(DESTDIR)/etc/default/netgwm
	install $(CURDIR)/netgwm $(DESTDIR)/usr/sbin/netgwm
