all:
	python setup.py build
	cd examples && ln -sf ../build/lib*/pyxmpp .
	cd examples && chmod a+x *.py
	cd tests && ln -sf ../build/lib*/pyxmpp .
	cd tests && chmod a+x *.py
