#!/bin/sh

PYLINT="${PYLINT:-pylint}"
BUILD="${BUILD:-build}"

auxdir=`dirname $0`
if [ -z $topdir ]; then
	topdir="."
fi
cd $auxdir
auxdir=`pwd`
cd ..
topdir=`pwd`
cd "${BUILD}/lib"

if [ -n "$1" ] ; then
	${PYLINT} --rcfile $auxdir/pylintrc $1
else
	${PYLINT} --rcfile $auxdir/pylintrc pyxmpp2
fi
