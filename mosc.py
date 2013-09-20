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

import sys
import collections
import yaml
import oscinterface
import midiinterface

def value_transformer(r_in, r_out, before, after):
    return lambda value: after((before(value) + r_in[0]) * (r_out[1] - r_out[0]) / r_in[1] + r_out[0])


def value_transfer(interface, transformer, address):
    def value_transferer(value):
        return interface.send(address, transformer(value))
    return value_transferer


class Multi(object):
    def __init__(self, count, s_interface, m_interface):
        self.s_interface = s_interface
        self.m_interface = m_interface
        self.memory = [None] * count
        self.multi = []

    def add(self, address, transformer):
        self.multi.append((address, transformer))

    def multi_to_single(self, address, index, transformer):
        def func(value):
            self.memory[index] = transformer(value)
            if any(x is None for x in self.memory):
                return
            self.s_interface.send(address, *self.memory)
        return func

    def single_to_multi(self, *value):
        self.memory = list(value)
        for i, (address, transformer) in enumerate(self.multi):
            self.m_interface.send(address, transformer(self.memory[i]))


class MOSCInterface(object):
    def __init__(self, interface):
        interface.handler = self.handler
        self.interface = interface
        self.map = {}
        self.last_address = None

    def start(self):
        self.interface.start()

    def send(self, address, *value):
        if len(value) == 1:
            print "-> %s: %s" % (address, value[0]),
        else:
            print "-> %s: %s" % (address, value),
        self.interface.send(address, *value)

    def handler(self, address, *value):
        if address != self.last_address:
            self.last_address = address
            print
            print "%s:" % (address, )

        print "\r" + 100 * " " + "\r",
        print value,

        if address in self.map:
            self.map[address](*value)


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
    def __init__(self, address, index=0, range_min=0.0, range_max=1.0):
        self.address = address
        self.param = range_min, range_max
        self.index = index


class ValueMapperApp(object):
    def __init__(self, stream):
        data = yaml.load(stream)
        self.osc = MOSCInterface(oscinterface.OSCInterface(*data["interfaces"]["osc"]))
        self.midi = MOSCInterface(midiinterface.MidiInterface(*data["interfaces"]["midi"]))

        mapping = self.read_mapping(data)
        multis = self.get_multis(mapping)

        for addr, multi in multis.iteritems():
            self.osc.map[addr] = multi.single_to_multi

        for osc_part, midi_part, direction in mapping:
            if osc_part.address in multis:
                multi = multis[osc_part.address]
                if direction != "<":
                    multi.add(midi_part.address, self.osc_2_midi(osc_part, midi_part))
                if direction != ">":
                    self.midi.map[midi_part.address] = multi.multi_to_single(osc_part.address, osc_part.index, self.midi_2_osc(osc_part, midi_part)) 
            else:
                if direction != "<":
                    self.osc.map[osc_part.address] = value_transfer(self.midi, self.osc_2_midi(osc_part, midi_part), midi_part.address)
                if direction != ">":
                    self.midi.map[midi_part.address] = value_transfer(self.osc, self.midi_2_osc(osc_part, midi_part), osc_part.address)

    @staticmethod
    def osc_2_midi(osc_part, midi_part):
        return value_transformer(osc_part.param, midi_part.param, float, int)

    @staticmethod
    def midi_2_osc(osc_part, midi_part):
        return value_transformer(midi_part.param, osc_part.param, float, float)

    def read_mapping(self, data):
        mapping = []
        for mapparts in data["mapping"]:
            if len(mapparts) > 2:
                direction = mapparts[2]
                mapparts = mapparts[:2]
            else:
                direction = "="

            osc_part = self.read_part(mapparts[0], OSCValueMapPart)
            midi_part = self.read_part(mapparts[1], MidiValueMapPart)

            mapping.append((osc_part, midi_part, direction))
        return mapping

    def get_multis(self, mapping):
        multi_max = collections.defaultdict(int)
        for osc_part, midi_part, direction in mapping:
            if osc_part.index > 0:
                multi_max[osc_part.address] = max(multi_max[osc_part.address], osc_part.index)
        return dict((addr, Multi(mx + 1, self.osc, self.midi)) for addr, mx in multi_max.iteritems())

    def read_part(self, part, reader):
        if isinstance(part, list):
            return reader(*part)
        else:
            return reader(part)

    def start(self):
        self.osc.start()
        self.midi.start()


if __name__ == "__main__":
    mapname = sys.argv[1] if len(sys.argv) > 1 else "defaultmap.txt"
    app = ValueMapperApp(open(mapname))
    app.start()
    print "MOSC Started!"
    raw_input("Press return to finish...\n")
