DESTDIR="/"

.PHONY: all build test version dist update-doc doc cosmetics pylint.log pylint ChangeLog www publish

all: build test

build: version
	umask 022 ; python setup.py build
	-cd examples && rm -f pyxmpp2 2>/dev/null && ln -s ../build/lib*/pyxmpp2 .
	-cd examples && chmod a+x *.py
	-cd tests && rm -f pyxmpp2 2>/dev/null && ln -s ../build/lib*/pyxmpp2 .
	-cd tests && chmod a+x *.py

test:
	$(MAKE) -C tests tests

doc:
	$(MAKE) -C doc

update-doc:
	$(MAKE) -C doc update-doc

www:
	$(MAKE) -C doc www

publish:
	$(MAKE) -C doc publish

pylint:	pylint.log

pylint.log: build
	./auxtools/pylint.sh $(CHECK_MODULE) | tee pylint.log

ChangeLog: 
	test -d .git && make cl-stamp || :
	
cl-stamp: .git
	git log > ChangeLog
	touch cl-stamp

cosmetics:
	./auxtools/cosmetics.sh
	
version:
	python setup.py make_version

dist: build ChangeLog update-doc
	-rm -f MANIFEST
	python setup.py sdist

clean:
	python setup.py clean --all
	-rm -rf build/*

install: all
	umask 022 ; python setup.py install --root $(DESTDIR)
