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

import time
import pygame.midi as pym
import interface


class NRPNTransformer(object):
    def __init__(self):
        self.cc99 = 0
        self.cc98 = 0
        self.cc6 = 0
        self.cc38 = 0

    def modify(self, cc, value):
        if cc == 99:
            self.cc99 = value
            return True
        elif cc == 98:
            self.cc98 = value
            return True
        elif cc == 6:
            self.cc6 = value
            return True
        elif cc == 38:
            self.cc38 = value
            return True
        return False

    @property
    def nrpn(self):
        return (self.cc99 << 7) + self.cc98

    @property
    def value(self):
        return (self.cc6 << 7) + self.cc38


class MidiTransformer(object):
    def __init__(self):
        self.nrpns = [NRPNTransformer() for _ in xrange(16)]

    def transform(self, channel, code, data1, data2):
        if code == 0x8:
            return (channel, "noteoff", data1), data2
        if code == 0x9:
            return (channel, "noteon", data1), data2
        if code == 0xB:
            nrpntrans = self.nrpns[channel]
            if nrpntrans.modify(data1, data2):
                return (channel, "nrpn", nrpntrans.nrpn), nrpntrans.value
            return (channel, "cc", data1), data2
        raise Exception("Unknown code %s" % code)


class MidiInterface(interface.Interface):
    def __init__(self, in_name, out_name, sleep_time=0.005):
        super(MidiInterface, self).__init__()
        pym.init()
        self.in_device = self._getdevice(in_name, True)
        self.out_device = self._getdevice(out_name, False)
        self.last_nrpn = None
        self.transformer = MidiTransformer().transform
        self.sleep_time = sleep_time

    def _run(self):
        while True:
            while not self.in_device.poll() or self.handler is None:
                time.sleep(self.sleep_time)
            for event, timestamp in self.in_device.read(10):
                status, data1, data2, data3 = event
                self.handler(*self.transformer(status & 0xF, status >> 4, data1, data2))

    def send(self, address, value):
        channel, command, code = address
        getattr(self, command)(channel, code, value)

    def noteon(self, channel, key, velocity):
        self.out_device.note_on(key, velocity, channel)

    def noteoff(self, channel, key, velocity):
        self.out_device.note_off(key, velocity, channel)

    def cc(self, channel, cc, data):
        self.out_device.write_short(0xB0 | channel, cc, data)

    def nrpn(self, channel, nrpn, data):
        # TODO: Remove this True and test
        if True or self.last_nrpn != nrpn:
            self.cc(channel, 99, nrpn >> 7)
            self.cc(channel, 98, nrpn & 0x7F)
            self.last_nrpn = nrpn
        self.cc(channel, 6, data >> 7)
        self.cc(channel, 38, data & 0x7F)

    def _getdevice(self, name, is_input):
        for i in xrange(pym.get_count()):
            info = pym.get_device_info(i)
            if info[1] != name:
                continue
            if is_input:
                if info[2]:
                    return pym.Input(i)
            else:
                if info[3]:
                    return pym.Output(i)
        raise Exception("Interface (%s, input=%s) was not found!" % (name, is_input))

