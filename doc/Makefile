EPYDOC=epydoc

.PHONY: all doc update-doc clean check-epydoc check-docutils

RST2HTML=rst2html

all: doc

doc: doc-tstamp check-epydoc check-docutils

update-doc:
	-rm -f doc-tstamp
	$(MAKE) doc

doc-tstamp:
	$(MAKE) -C .. build
	if [ -L pyxmpp2 ] ; then rm pyxmpp2 ; fi
	ln -s ../build/lib*/pyxmpp2 .
	mkdir -p www/api
	$(EPYDOC) -v --include-log --html --config=epydoc.cfg -o www/api pyxmpp2
	touch doc-tstamp
	-rm -f pyxmpp2 2>/dev/null

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
	
clean:

.DELETE_ON_ERROR:
