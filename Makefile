BASE_VERSION=0.1
SNAPSHOT=

DESTDIR="/"

.PHONY: all version snapshot dist

all: version
	umask 022 ; python setup.py build
	cd examples && ln -sf ../build/lib*/pyxmpp .
	cd examples && chmod a+x *.py
	cd tests && ln -sf ../build/lib*/pyxmpp .
	cd tests && chmod a+x *.py

version:
	if test -n "$(SNAPSHOT)" ; then \
		SNAPSHOT=".$(SNAPSHOT)" ; \
	else \
		SNAPSHOT=.`find . -name "*.py" '!' -name "version.py" -printf '%TY%Tm%Td\n' | sort -r | head -1` ; \
	fi ; \
	echo "version='$(BASE_VERSION)$$SNAPSHOT'" > pyxmpp/version.py ; \

snapshot: version dist

dist:
	python setup.py sdist

install:
	umask 022 ; python setup.py install --root $(DESTDIR)
