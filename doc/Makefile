EPYDOC=epydoc

.PHONY: all doc check-epydoc check-docutils

all: doc

doc:	check-epydoc check-docutils
	$(MAKE) -C ..
	rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	$(EPYDOC) --html --show-imports --no-frames --ignore-param-mismatch -n PyXMPP -u http://jabberstudio.org/projects/pyxmpp pyxmpp
	-rm -f pyxmpp 2>/dev/null
	
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
	
