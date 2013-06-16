"""
MOSC - Midi OSC

See README.md for documentation

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

import collections
import itertools
import sys

import yaml

import midiinterface
import oscinterface
import valuemapper


class MapPart(object):
    def __repr__(self):
        return "%s(%s, %s)" % (type(self).__name__, self.address, self.param)


class MidiValueMapPart(MapPart):
    def __init__(self, code, type="nrpn", range_min=0, range_max=None, channel=0):
        self.address = channel, type, code
        if range_max is None:
            range_max = 16383 if type == "nrpn" else 127
        self.param = range_min, range_max


class OSCValueMapPart(MapPart):
    def __init__(self, address, range_min=0.0, range_max=1.0):
        self.address = address
        self.param = range_min, range_max


class ValueMapperApp(object):
    def __init__(self, stream, defs):
        data = yaml.load(stream)
        self.interfaces = [defs[name].interface(*params) for name, params in data["interfaces"]]
        names = [x[0] for x in data["interfaces"]]

        mappartreaders = [defs[name].mappart for name in names]
        mapping = []
        for mapparts in data["mapping"]:
            single_mapping = []
            for reader, part in itertools.izip(mappartreaders, mapparts):
                if part is None:
                    value = None
                elif isinstance(part, list):
                    value = reader(*part)
                else:
                    value = reader(part)
                single_mapping.append(value)
            mapping.append(single_mapping)

        def gettransformer(before, after):
            def single(r_in, r_out, value):
                return after((before(value) + r_in[0]) * (r_out[1] - r_out[0]) / r_in[1] + r_out[0])
            return single

        mappers = [[gettransformer(defs[a].before, defs[b].after) for b in names] for a in names]
        valuemapper.ValueMapper(self.interfaces, mapping, mappers)

    def start(self):
        for interface in self.interfaces:
            interface.start()


if __name__ == "__main__":
    InterfaceDef = collections.namedtuple("InterfaceDef", "interface mappart before after")
    defs = {"midi": InterfaceDef(midiinterface.MidiInterface, MidiValueMapPart, float, int),
            "osc": InterfaceDef(oscinterface.OSCInterface, OSCValueMapPart, float, float)}

    mapname = sys.argv[1] if len(sys.argv) > 1 else "defaultmap.txt"
    app = ValueMapperApp(open(mapname), defs)
    app.start()
    print "MOSC Started!"
    raw_input("Press return to finish...\n")
