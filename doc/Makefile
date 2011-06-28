EPYDOC=epydoc

.PHONY: all doc update-doc clean check-epydoc check-docutils update-settings

RST2HTML=rst2html
PYTHON=python
PYXMPP2_PATH=$(firstword $(wildcard ../build/lib*))

all: doc

doc: doc-tstamp check-epydoc check-docutils

update-doc:
	-rm -f doc-tstamp
	$(MAKE) doc

doc-tstamp:
	$(MAKE) -C .. build
	mkdir -p www/api
	$(MAKE) update-settings
	PYTHONPATH="$(PYXMPP2_PATH):$$PYTHONPATH" \
	$(EPYDOC) -v --include-log --html --config=epydoc.cfg -o www/api pyxmpp2
	touch doc-tstamp

check-epydoc:
	@if ! $(EPYDOC) --help >/dev/null ; then \
		echo "*************************************************" ; \
		echo "You need Epydoc to generate PyXMPP documentation." ; \
		echo "You can find it at http://epydoc.sourceforge.net/" ; \
		echo "*************************************************" ; \
		exit 1 ; \
	fi
	
check-docutils:
	@if ! python -c "import docutils" --help >/dev/null ; then \
		echo "*****************************************************" ; \
		echo "You need docutils to generate PyXMPP documentation.  " ; \
		echo "You can find them at http://docutils.sourceforge.net/" ; \
		echo "*****************************************************" ; \
		exit 1 ; \
	fi

Settings.rst settings.txt: update-settings

update-settings:
	PYTHONPATH="$(PYXMPP2_PATH):$$PYTHONPATH" $(PYTHON) make_settings_doc.py

www/Settings.html: Settings.rst
	$(RST2HTML) Settings.rst www/Settings.html
	
clean:

.DELETE_ON_ERROR:
