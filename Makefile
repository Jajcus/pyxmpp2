VERSION=0.3

DESTDIR="/"

.PHONY: all version snapshot dist

all: version
	umask 022 ; python setup.py build
	-cd examples ; rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	-cd examples ; chmod a+x *.py
	-test -d examples/jjigw && cd examples/jjigw \
		&& rm -f pyxmpp 2>/dev/null \
		&& ln -s ../../build/lib*/pyxmpp .\
		&& chmod a+x jjigw.py
	-cd tests ; rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	-cd tests ; chmod a+x *.py
	
version:
	if test -f "CVS/Entries" ; then \
		echo "version='$(VERSION)+cvs'" > pyxmpp/version.py ; \
	fi

dist: all
	echo "version='$(VERSION)'" > pyxmpp/version.py
	python setup.py sdist

clean:
	python setup.py clean

install: all
	umask 022 ; python setup.py install --root $(DESTDIR)
