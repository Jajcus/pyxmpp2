all:
	python setup.py build
	cd examples && ln -sf ../build/lib*/pyxmpp .
	cd tests && ln -sf ../build/lib*/pyxmpp .
