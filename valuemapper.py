"""
Copyright (c) 2013 by Tomer Altman <tomer.altman@gmail.com>

This file is part of MOSC.

MOSC is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

MOSC is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with MOSC.  If not, see <http://www.gnu.org/licenses/>.
"""

class ValueMapper(object):
    def __init__(self, interfaces, mapping, transformers):
        self.interfaces = interfaces
        for i, interface in enumerate(interfaces):
            interface.handler = self._gethandler(i)

        self.mappings = []
        for i in xrange(len(interfaces)):
            self.mappings.append(dict((mapparts[i].address, mapparts) for mapparts in mapping if mapparts[i] is not None))

        self.transformers = transformers
        self.last_address = None

    def _gethandler(self, interfaceid):
        def handle(address, value):
            return self._handle(address, value, interfaceid)
        return handle

    def _handle(self, address, value, interfaceid):
        if address != self.last_address:
            self.last_address = address
            print
            print "%s:" % (address, )

        print "\r" + 100 * " " + "\r",
        print value,

        if address not in self.mappings[interfaceid]:
            return

        mapparts = self.mappings[interfaceid][address]
        param_in = mapparts[interfaceid].param
        for i, mappart in enumerate(mapparts):
            if i == interfaceid or mappart is None:
                continue

            value = self.transformers[interfaceid][i](param_in, mappart.param, value)
            print "-> %s: %s" % (mappart.address, value),
            self.interfaces[i].send(mappart.address, value)
