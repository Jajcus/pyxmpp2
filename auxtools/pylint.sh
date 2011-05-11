#!/bin/sh

auxdir=`dirname $0`
if [ -z $topdir ]; then
	topdir="."
fi
cd $auxdir
auxdir=`pwd`
cd ..
#make >&2
topdir=`pwd`
cd build/lib

if [ -n "$1" ] ; then
	pylint --rcfile $auxdir/pylintrc $1
else
	pylint --rcfile $auxdir/pylintrc pyxmpp2
fi
