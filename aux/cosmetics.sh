#!/bin/sh

dir=`dirname $0`
find . -name "*.py" | xargs -n1 vim -u NONE -s $dir/cosmetics.vim --cmd ":set ts=8"
stty sane
