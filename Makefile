BASE_VERSION=0.2
RELEASE=

DESTDIR="/"

.PHONY: all version snapshot dist

all: version
	umask 022 ; python setup.py build
	cd examples ; rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	cd examples ; chmod a+x *.py
	cd tests ; rm -f pyxmpp 2>/dev/null ; ln -sf ../build/lib*/pyxmpp .
	cd tests ; chmod a+x *.py
	
version:
	if test -f "CVS/Entries" ; then \
		if [ "x$(RELEASE)" != "x" ]; then \
			SNAPSHOT="" ; \
		else \
			SNAPSHOT=.`find . -name "*.py" '!' -name "version.py" -printf '%TY%Tm%Td_%TH%TM\n' | sort -r | head -1 2>/dev/null || echo unknown` ; \
		fi ; \
		echo "version='$(BASE_VERSION)$$SNAPSHOT'" > pyxmpp/version.py ; \
	fi

dist: all
	python setup.py sdist

clean:
	python setup.py clean

install: all
	umask 022 ; python setup.py install --root $(DESTDIR)
