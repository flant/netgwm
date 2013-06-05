all: stamp

stamp:
	touch stamp

install:
	install -d $(DESTDIR)/usr/lib/netgwm/
	install -d $(DESTDIR)/var/lib/netgwm/
	install -d $(DESTDIR)/etc/netgwm/
	cp -r $(CURDIR)/samples/* $(DESTDIR)/etc/netgwm/
	install $(CURDIR)/netgwm.py $(DESTDIR)/usr/lib/netgwm/netgwm.py
