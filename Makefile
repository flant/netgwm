all: stamp

stamp:
	touch stamp

install:
	install -d $(DESTDIR)/usr/sbin
	install -d $(DESTDIR)/etc
	cp -r $(CURDIR)/gwm $(DESTDIR)/etc
	install $(CURDIR)/gwm.py $(DESTDIR)/usr/sbin/gwm
