from __future__ import absolute_import
from __future__ import division

import re

from pydicti import dicti, odicti       # for direct export


__all__ = [
    'dicti',
    'odicti',
    'none_checked',
    'stri',
    'Re',
]

#----------------------------------------
# Utilities
#----------------------------------------

def none_checked(type):
    """Create a simple ``None``-checked constructor."""
    def constructor(value):
        return None if value is None else type(value)
    constructor.cls = type
    return constructor


@none_checked
class stri(str):
    """Case insensitive string."""
    def __eq__(self, other):
        return self.lower() == str(other).lower()
    def __ne__(self, other):
        return not (self == other)


class Re(object):

    """
    Precompiled regular expressions that remembers the expression string.

    Inherits from :class:`re.SRE_Pattern` by delegation.

    :ivar str s: string expression
    :ivar SRE_Pattern r: compiled regex
    """

    def __init__(self, *args):
        """Concat the arguments."""
        self.s = ''.join(map(str, args))
        self.r = re.compile(self.s)

    def __str__(self):
        """Return the expression that was used to create the regex."""
        return self.s

    def __getattr__(self, key):
        """Delegate attribute access to the precompiled regex."""
        return getattr(self.r, key)
