#
# (C) Copyright 2011 Jacek Konieczny <jajcus@jajcus.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License Version
# 2.1 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

"""SASLprep stringprep profile.

Normative reference:
  - :RFC:`4013`__
"""

from __future__ import absolute_import, division

__docformat__ = "restructuredtext en"

import stringprep

from ..xmppstringprep import Profile, b1_mapping, c12_mapping, nfkc

SASLPREP = Profile(
    unassigned = (stringprep.in_table_a1,),
    mapping = (b1_mapping, c12_mapping),
    normalization = nfkc,
    prohibited = (  stringprep.in_table_c12, stringprep.in_table_c21,
                    stringprep.in_table_c22, stringprep.in_table_c3,
                    stringprep.in_table_c4, stringprep.in_table_c5,
                    stringprep.in_table_c6, stringprep.in_table_c7,
                    stringprep.in_table_c8, stringprep.in_table_c9 ),
    bidi = True)

# vi: sts=4 et sw=4
