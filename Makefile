VERSION=0.5

DESTDIR="/"

.PHONY: all version snapshot dist doc

all: version
	umask 022 ; python setup.py build
	-cd examples ; rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	-cd examples ; chmod a+x *.py
	-cd tests ; rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	-cd tests ; chmod a+x *.py

doc:
	$(MAKE) -C doc

ChangeLog: FORCE
	svn log -v --xml | svn2log.py -p '/(branches/[^/]+|trunk)' -x ChangeLog -u aux/users
	
FORCE:
	
version:
	if test -d ".svn" ; then \
		echo "version='$(VERSION)+svn'" > pyxmpp/version.py ; \
	fi

dist: all
	echo "version='$(VERSION)'" > pyxmpp/version.py
	python setup.py sdist

clean:
	python setup.py clean --all

install: all
	umask 022 ; python setup.py install --root $(DESTDIR)
