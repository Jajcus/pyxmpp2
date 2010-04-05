VERSION=1.1.0
SNAPSHOT=

DESTDIR="/"

.PHONY: all build test version dist update-doc doc cosmetics TODO.pylint pylint ChangeLog www publish

all: build test

build: version
	umask 022 ; python setup.py build
	-cd examples ; rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	-cd examples ; chmod a+x *.py
	-cd tests ; rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	-cd tests ; chmod a+x *.py

test:
	$(MAKE) -C tests

doc:
	$(MAKE) -C doc

update-doc:
	$(MAKE) -C doc update-doc

www:
	$(MAKE) -C doc www

publish:
	$(MAKE) -C doc publish

pylint:	TODO.pylint

TODO.pylint:
	./auxtools/pylint.sh | tee TODO.pylint

ChangeLog: 
	test -f .svn/entries && make cl-stamp || :
	
cl-stamp: .svn/entries
	TZ=UTC svn log -v --xml \
		| auxtools/svn2log.py -p '/(branches/[^/]+|trunk)' -x ChangeLog -u auxtools/users -F
	touch cl-stamp

cosmetics:
	./auxtools/cosmetics.sh
	
version:
	if test -d ".svn" ; then \
		echo "# pylint: disable-msg=W0103,W0131" > pyxmpp/version.py ; \
		echo "version='$(VERSION)+svn'" >> pyxmpp/version.py ; \
	fi

dist: build ChangeLog
	-rm -f MANIFEST
	echo "version='$(VERSION)$(SNAPSHOT)'" > pyxmpp/version.py
	python setup.py sdist

clean:
	python setup.py clean --all
	-rm -rf build/*

install: all
	umask 022 ; python setup.py install --root $(DESTDIR)
