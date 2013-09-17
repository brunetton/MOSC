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

import xml.etree.ElementTree as ET
import StringIO

class CubaseMapper(object):
    PUSH     = 0b0000000001
    TOGGLE   = 0b0010000000
    NO_AUTO  = 0b1000000000

    def __init__(self):
        self.root = ET.Element("remotedescription", version="1.1")
        self.ctrltable = ET.SubElement(self.root, "ctrltable", name="Standard MIDI")
        self.ctrltable.text = self.ctrltable.tail = "\n"
        self.bank = ET.SubElement(self.root, "bank", name="1")
        self.bank.text = self.bank.tail = "\n"
        self.name_index = 0

    def add_mapping(self, address, name, flags=0, relative=False):
        entryname = self._addctrl(address, relative)
        entry = self._addentry(entryname)
        parts = name.split(";")
        if len(parts) == 2:
            category, action = parts
            self._addcommand(entry, category, action)
        elif len(parts) == 3:
            device, channel, name = parts
            self._addvalue(entry, device, channel, name, flags)
        else:
            raise Exception("wtf %s" % (parts,))

    def _addentry(self, entryname):
        entry = ET.SubElement(self.bank, "entry", ctrl=entryname)
        entry.tail = "\n"
        return entry

    STATS = {"noteon": "144", "cc": "176", "nrpn": "2"}
    MAXES = {"noteon": "127", "cc": "127", "nrpn": "16383"}
    RECEIVE  = 0b000000001
    TRANSMIT = 0b000000010
    RELATIVE = 0b000000100
    NRPN     = 0b000001000
    def _addctrl(self, address, relative):
        ctrl = ET.SubElement(self.ctrltable, "ctrl")
        ctrl.tail = "\n"
        
        name = "Ctrl %d" % self.name_index
        self.name_index += 1

        type, channel, code = address
        ET.SubElement(ctrl, "name").text = name
        ET.SubElement(ctrl, "stat").text = self.STATS[type]
        ET.SubElement(ctrl, "chan").text = str(channel)
        ET.SubElement(ctrl, "addr").text = str(code)
        ET.SubElement(ctrl, "max").text = self.MAXES[type]
        
        flags = self.RECEIVE
        if type == "nrpn":
            flags |= self.NRPN
        flags |= self.RELATIVE if relative else self.TRANSMIT
        ET.SubElement(ctrl, "flags").text = str(flags)

        return name

    def _addcommand(self, entry, category, action):
        command = ET.SubElement(entry, "command")
        ET.SubElement(command, "category").text = category
        ET.SubElement(command, "action").text = action
        ET.SubElement(command, "flags").text = str(self.PUSH)

    def _addvalue(self, entry, device, channel, name, flags):
        value = ET.SubElement(entry, "value")
        ET.SubElement(value, "device").text = device
        if channel.lower() == "selected":
            channel = -2
        elif channel.lower() == "device":
            channel = -1
        ET.SubElement(value, "chan").text = str(channel)
        ET.SubElement(value, ("tag" if name.isdigit() else "name")).text = name
        ET.SubElement(value, "flags").text = str(flags)

    def dump(self):
        s = StringIO.StringIO()
        ET.ElementTree(self.root).write(s, "UTF-8")
        return s.getvalue()
