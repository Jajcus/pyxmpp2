

all: doc

doc:
	$(MAKE) -C ..
	rm -f pyxmpp 2>/dev/null ; ln -s ../build/lib*/pyxmpp .
	epydoc --html --show-imports --no-frames -n PyXMPP -u http://jabberstudio.org/projects/pyxmpp pyxmpp
	-rm -f pyxmpp 2>/dev/null
