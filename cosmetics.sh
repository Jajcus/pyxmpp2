#!/bin/sh

find . -name "*.py" | xargs -n1 vim -u NONE -s cosmetics.vim --cmd ":set ts=8"
stty sane
