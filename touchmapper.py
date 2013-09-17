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

import zipfile
import sys
import os
import xml.etree.ElementTree as ET

import yaml

import cubasemapper

"""
Controller:
types: fader, rotary, multifader, multirotary, xy
mosc: [osc, code]
cubase: nrpn, code, (0, 16383), N?

Command:
types: toggle, push, multitoggle, multipush
mosc: [osc, (code, "noteon")]
cubase: note, code, (0, 127), P?T?N?

Relative:
types: encoder, push*2
mosc:
 encoder: [osc, (code, "noteon", 1, 127)]
 button+: [osc, (code, "noteon", 0, 127)]
 button-: [osc, (code, "noteon", 0, 1)]
cubase: note, code, (0, 127), RPT?N?
"""

class LayoutMapper(object):
    def __init__(self, tree, cubase_mapper):
        self.tree = tree
        self.moscmap = []
        self.cubase_mapper = cubase_mapper

        self.last_nrpn = -1
        self.last_note = -1

    def _generatenrpn(self):
        self.last_nrpn += 1
        return self.last_nrpn

    def _generatenote(self):
        self.last_note += 1
        return self.last_note

    def _parsename(self, name):
        if "|" not in name:
            return name, 0, 0, None
        
        name, flags = name.rsplit("|", 1)

        rel = 0
        if "+" in flags:
            rel = 1
        elif "-" in flags:
            rel = -1

        flagsval = 0
        if "P" in flags:
            flagsval |= self.cubase_mapper.PUSH
        if "T" in flags:
            flagsval |= self.cubase_mapper.TOGGLE
        if "N" in flags:
            flagsval |= self.cubase_mapper.NO_AUTO

        return name, flagsval, rel, (">" in flags)

    def handle_single_cont(self, osc, name):
        nrpn = self._generatenrpn()
        name, flagsval, rel, onewayvalue = self._parsename(name)
        self.cubase_mapper.add_mapping(("nrpn", 0, nrpn), name, flagsval, rel != 0)
        self.moscmap.append([osc, nrpn])

    def handle_single_button(self, osc, name):
        note = self._generatenote()
        name, flags, rel, onewayvalue = self._parsename(name)
        self.cubase_mapper.add_mapping(("noteon", 0, note), name, flags, rel != 0)
        if rel < 0:
            self.moscmap.append([osc, [note, "noteon", 0, 1]])
        elif onewayvalue is not None:
            self.moscmap.append([osc, [note, "noteon"], ">"])
        else:
            self.moscmap.append([osc, [note, "noteon"]])

    def handle_encoder(self, osc, name):
        note = self._generatenote()
        name, flags, rel, onewayvalue = self._parsename(name)
        self.cubase_mapper.add_mapping(("noteon", 0, note), name, flags, relative=True)
        self.moscmap.append([osc, [note, "noteon", 1, 127]])

    def handle_multi(self, osc, name, number, single):
        for i in xrnage(number):
            # TODO: Allow offset from x
            single(osc + "/" + str(i), name.replace("<x>", str(i)))

    def get_single_handler(self, name):
        if name in ["faderv", "faderh", "rotaryv", "rotaryh"]:
            return self.handle_single_cont
        if name in ["toggle", "push"]:
            return self.handle_single_button
        if name == "encoder":
            return self.handle_encoder

    def generatemapping(self):
        assert self.tree.get("version") == "13"
        for control in self.tree.findall("tabpage/control"):
            name = control.get("name").decode("base64")
            if ";" not in name:
                continue
            
            type = control.get("type")
            osc_cs = control.get("osc_cs")
            if osc_cs is None:
                continue
            osc_cs = osc_cs.decode("base64") 

            if type == "xy":
                partx, party = name.split(",")
                self.handle_single_button([osc_cs, 0], partx)
                self.handle_single_button([osc_cs, 1], party)
                continue

            if type.startswith("multi"):
                self.handle_multi(cs_osc, name, control.get("number"), self.get_single_handler(type[5:]))
                continue
            self.get_single_handler(type)(osc_cs, name)


if __name__ == "__main__":
    # TODO: More usable configuration. GUI?
    layoutpath, moscpath, remotepath, oscport, cubasetomosc, mosctocubase = sys.argv[1:]
    
    zf = zipfile.ZipFile(layoutpath)
    for name in zf.namelist():
        if os.path.basename(name) == "index.xml":
            tree = ET.fromstring(zf.read(name))
            break
    
    cm = cubasemapper.CubaseMapper()
    lm = LayoutMapper(tree, cm)
    lm.generatemapping()
    mosc_config = {"interfaces": {"osc": [int(oscport)], "midi": [cubasetomosc, mosctocubase]},
                   "mapping": lm.moscmap}
    yaml.dump(mosc_config, open(moscpath, "w"))
    open(remotepath, "w").write(cm.dump())
    