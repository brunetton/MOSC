MOSC - Midi OSC
===============
Goals:
- Provide high-performance and high-precision mapping of OSC clients to music applications lacking built-in OSC support.
- Provide a simple way to perform said mapping.

The project currently consists of two parts:
- A simple bridge between OSC (OpenSoundControl http://opensoundcontrol.org/) and a Midi interface
- A map generator which can read TouchOSC (http://hexler.net/software/touchosc) layout files and generate mappings for MOSC and a generic remote xml for Cubase.

Used libraries:
- OSC support is provided by the included pysc library. I might pull it to another repository as its own library.
- Midi support is provided by PortMidi through the pygame bundle (http://www.pygame.org/).
- yaml support is provided by pyyaml (http://pyyaml.org/).

Being a very early version:
- The state of documentation is non-existent.
- The API very open to change.


Usage
=====
MOSC:
mosc.py mapname.txt

TouchOSC layout mapper:
touchlayout.py path_to_layout output_path_to_map output_path_to_generic_remote


Map files
=========
The MOSC map file is in yaml format as follows through example:

```yaml
interfaces: # List of interfaces, one OSC and one Midi
  osc: 10000 # OSC initializer. Only one port is used for input and output. Client IP can be added after the port number.
  midi: [LM Cubase to MOSC, LM MOSC to Cubase] # Midi initializer. These are names of the Midi interfaces to use.
                                               # Usually this would be a virtual devices such as LoopMidi (http://www.tobias-erichsen.de/software/loopmidi.html)
                                               # The first interface is INPUT for MOSC and the second is OUTPUT from MOSC.
mapping:    # This is the mapping of interfaces, the values are ordered as in the interfaces above
- [/1/volume, 10]   # This maps OSC address "/1/volume" from values 0.0-1.0 to the Midi NRPN 10, to values 0-16383
- [/1/pan, 11]      # If no further value is written, (NRPN, 0-16383, channel 0) will be used.
- [/1/mute, [10, "noteon"]] # If different values are needed, the values must be given as a lsit
- [/1/play, [12, "noteon", 0, 127, 3]]  # Further values are rangemin, rangemax and channel
- [/encoderM, [11, "noteon", 1, 127]]   # Relative values should be given between 1 and 127 for Cubase to process them as expected
- [[/5/xy1, 0], 13]  # xy pads send 2 values instead of one. In order to decide which one is mapped, the index is given in a tuple
- [[/5/xy1, 1], 14, ">"]  # The Y value goes to NRPN 14 while the X value goes to NRPN 13. Values are sent from OSC to midi, but not back.
```

Mapping TouchOSC layouts
========================
Layouts must be of version 13 which is the current version of the layout manager.
Most types of controls are supported by the system.
Values are mapped into Midi controls, both to the MOSC mapper and a Generic Remote XML for Cubase to use.
The actual values used should be of no concern.
Automatic mapping uses the "name" attribute for a TouchOSC widget. The values are mapped to "entries" in the Generic Remote XML.
Two types exist:
Value - These are controllers in the DAW. Examples: Channel volume, Mute control. These are transmitted back to the mapper for updating the layout.
Command - These are one-shots, performing a command in the DAW. Examples: Play, Record.
These types are mapped differently, according to the number of values required for each.

Example:
Mixer;Selected;Volume - This would be mapped to the entry "<value><device>Mixer</device><chan>-2</chan><name>Volume</name><flags>0</flags></value>" in the generic remote.
  |      |       \
device   |        name
      channel
    either a number
    or selected -> -2
    or device -> -1

Commands are given using only two values such as "Transport;Stop".

According to the controller used, different Midi messages would be mapped.
Faders and Rotaries are mapped to NRPNs.
Toggles and Push are mapped to noteon
Encoder is mapped to noteon with range of 1, 127 and set to relative.

Optional flags are gives as follows:
Mixer;Selected;Volume|PTN <-- P, T and N are the same as in the Generic Remote page in Cubase (Push button, Toggle, Not Automated).

In order to set a button to perform a relative action, the flags "+" or "-" should be used.
These will set the buttons to the ranges 0, 127 and and 0, 1 respectively and add the Relative flag in the Generic Remote section.

Multi controls will replace a "<x>" value in the name with a running number from 0 to the count of values in the control.
Mixer;<x>;Volume on a 8 bar multifader will add 8 mappings, for channels from 0 to 7.
(Future note, more manipulations will be added to allow offset from the given "x")

xy controllers are split by a comma.
For example, Mixer;Selected;eq1:freq,Mixer;Selected;eq1:gain will give a nice visual representation of the peak in the Cubase equalizer.
    
History
=======
As a novice music creator, I have sought a smoother control method than using the keyboard and mouse for fine tuning aspects in a DAW (Digital Audio Workstation).
I have acquired a midi controller with knobs and faders, believing this is a good method to control the application.
Unfortunately, the midi interface was proving not as precise as I expected, supporting only 128 levels of precision. This was not enough.
I then found the OSC protocol, being a modern descendant of Midi, providing excellent precision and modern control applications such as TouchOSC.
Unfortunately again, my DAW of choice (Steinberg Cubase) does not have support for the OSC protocol.
Searching the net for bridging applications, the applications I have found which seemed useful enough, did not support 14-bit precision mapping through NRPN,
leaving me again with the 7-bit precision I was trying to avoid.
Being a programmer for a living, I decided enough is enough. The protocols seemed simple enough to work with so this application was born.
Hopefully, it would help others looking for a suitable solution and possibly push even the most stubborn of music applications into the 21st century.


Copyright
=========
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