:set nocompatible
:%s/\s\+$//
:g/^# \(vi\): /d
:set et
:retab!
:$
:append
# vi: sts=4 et sw=4
.
:update
:q
:q!
