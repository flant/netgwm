all: stamp

stamp:
	touch stamp

install:
	install -d $(DESTDIR)/usr/lib/netgwm/
	install -d $(DESTDIR)/etc/
	install -d $(DESTDIR)/var/lib/netgwm
	cp -r $(CURDIR)/netgwm $(DESTDIR)/etc/
	install $(CURDIR)/netgwm.py $(DESTDIR)/usr/lib/netgwm/netgwm.py
