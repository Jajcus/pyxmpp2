VERSION=0.5
SNAPSHOT=

DESTDIR="/"

.PHONY: all version snapshot dist doc ChangeLog cosmetics TODO.pylint pylint

all: version
	umask 022 ; python setup.py build
	-cd examples ; rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	-cd examples ; chmod a+x *.py
	-cd tests ; rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	-cd tests ; chmod a+x *.py

doc:
	$(MAKE) -C doc

ChangeLog: 
	TZ=UTC svn log -v --xml | svn2log.py -p '/(branches/[^/]+|trunk)' -x ChangeLog -u aux/users

pylint:	TODO.pylint

TODO.pylint:
	./aux/pylint.sh | tee TODO.pylint

cosmetics:
	./aux/cosmetics.sh
	
version:
	if test -d ".svn" ; then \
		echo "version='$(VERSION)+svn'" > pyxmpp/version.py ; \
	fi

dist: all
	echo "version='$(VERSION)$(SNAPSHOT)'" > pyxmpp/version.py
	python setup.py sdist

clean:
	python setup.py clean --all

install: all
	umask 022 ; python setup.py install --root $(DESTDIR)
