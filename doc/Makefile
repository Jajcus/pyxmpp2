EPYDOC=epydoc

.PHONY: all doc update-doc clean check-epydoc check-docutils \
	pyxmpp.xmi pyxmpp-auto.xmi

WEBFILES=www/index.html www/CHANGES.html www/ChangeLog.html \
	www/style.css

RST2HTML=rst2html.py

all: doc

www: $(WEBFILES) doc

doc: doc-tstamp check-epydoc check-docutils

update-doc:
	-rm -f doc-tstamp
	$(MAKE) doc

doc-tstamp:
	$(MAKE) -C ..
	rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	$(EPYDOC) --html --show-imports --no-frames \
		-o www/api -n PyXMPP -u http://pyxmpp.jajcus.net/ pyxmpp
	touch doc-tstamp
	-rm -f pyxmpp 2>/dev/null

pyxmpp.xmi: 
	[ -f pyxmpp.xmi ]
	[ -f pyxmpp-auto.xmi ]
	[ ! -f pyxmpp.xmi.bak ]
	mv pyxmpp.xmi pyxmpp.xmi.bak
	../auxtools/xmimerge.py pyxmpp.xmi.bak pyxmpp-auto.xmi > pyxmpp.xmi

pyxmpp-auto.xmi:
	rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	../auxtools/code2xmi.py pyxmpp > pyxmpp-auto.xmi
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
	
index.html: ../README
	$(RST2HTML) --link-stylesheet --rfc-references --initial-header-level=2 ../README > index.html

CHANGES.html: ../CHANGES
	$(RST2HTML) --link-stylesheet --rfc-references --initial-header-level=2 --no-doc-title ../CHANGES > CHANGES.html

ChangeLog.html: ../ChangeLog
	echo -ne '<div class="document">\n<h2>ChangeLog</h2>\n<pre>' > ChangeLog.html
	sed -e's/&/\&amp;/;s/</\&lt;/;s/>/\&gt;/' ../ChangeLog >> ChangeLog.html
	echo -ns '</pre>\n</div>\n' >> ChangeLog.html

www/%.html: %.html template.html
	../auxtools/htmlmerge.py template.html $*.html \
	  | xmllint --nsclean - | sed -e's/name="\([^"]*\)" id="\1"/name="\1"/g' > $@

clean:
	-rm -f index.html CHANGES.html ChangeLog.html
	-rm -f pyxmpp-auto.xmi

.DELETE_ON_ERROR:
