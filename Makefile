all: stamp

stamp:
	touch stamp

install:
	install -d $(DESTDIR)/usr/sbin
	install -d $(DESTDIR)/etc
	cp -r $(CURDIR)/netgwm $(DESTDIR)/etc
	install $(CURDIR)/netgwm.py $(DESTDIR)/usr/sbin/netgwm
