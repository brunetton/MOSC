"""
Copyright (c) 2013 by Tomer Altman <tomer.altman@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import SocketServer
import socket
import struct
import math
import time
import datetime
import types


def _maketype(name, base):
    return type(name, (base, ), {"__repr__": lambda self: "%s(%s)" % (name, base.__repr__(self))})

Time = _maketype("Time", float)
Blob = _maketype("Blob", str)


class Message(object):
    def __init__(self, address, *args):
        self.address, self.args = address, args

    def __eq__(self, other):
        return self.address == other.address and self.args == other.args

    def __repr__(self):
        return 'Message(address="' + self.address + '", ' + ', '.join((repr(arg) for arg in self.args)) + ')'


class Bundle(object):
    def __init__(self, timetag, *elements):
        self.elements = elements
        self.timetag = timetag if isinstance(timetag, Time) else Time(timetag)

    def __eq__(self, other):
        return self.timetag == other.timetag and self.elements == other.elements

    def __repr__(self):
        return 'Bundle(timetag=' + str(self.timetag) + ', ' + ', '.join((repr(element) for element in self.elements)) + ')'


NTP_DELTA = (datetime.date(*time.gmtime(0)[0:3]) - datetime.date(1900, 1, 1)).days * 24 * 3600
NTP_UNITS = 0x100000000


def serialize(message):
    def _null(value):
        return ""
    
    def _int(value):
        return struct.pack('>i', value)

    def _float(value):
        return struct.pack('>f', value)

    def _string(value):
        length = len(value)
        length += (3 - length) % 4
        return struct.pack(str(length) + 'ss', value, '\x00')

    def _time(value):
        if value < 0.0:
            return struct.pack('>LL', 0L, 1L)
        fractional, seconds = math.modf(value)
        fractional = int(fractional * NTP_UNITS)
        if fractional >= NTP_UNITS:
            fractional = NTP_UNITS - 1
        return struct.pack('>LL', seconds + NTP_DELTA, fractional)

    def _blob(value):
        length = len(value)
        padded = length + (4 - length) % 4
        return struct.pack('>i' + str(padded) + 's', length, value)

    mapping = {int: ("i", _int),
               str: ("s", _string),
               Time: ("t", _time),
               Blob: ("b", _blob),
               float: ("f", _float),
               types.NoneType: ("N", _null)}

    if isinstance(message, Bundle):
        buffer = [_string("#bundle")]
        buffer.append(_time(message.timetag))        
        for element in message.elements:
            data = serialize(element)
            buffer.append(_int(len(data)))  
            buffer.append(data)
        return "".join(buffer)

    # Message
    buffer = [_string(message.address), None]
    typetags = [","]
    for arg in message.args:
      tag, serializer = mapping[type(arg)]
      buffer.append(serializer(arg))
      typetags.append(tag)
    buffer[1] = _string("".join(typetags))
    return "".join(buffer)


class DeserializerStream(object):
    def __init__(self, packet):
        self.packet = packet
        self.offset = 0

    def _unpack(self, fmt):
        value = struct.unpack_from(fmt, self.packet, self.offset)[0]
        self.offset += struct.calcsize(fmt)
        return value

    def _pad(self):
        self.offset += (4 - self.offset) % 4

    def _int(self):
        return self._unpack('>i')

    def _float(self):
        return self._unpack('>f')

    def _null(self):
        return None

    def _time(self):
        seconds = self._unpack('>L')
        fractional = float(self._unpack('>L'))
        fractional /= NTP_UNITS
        return Time(seconds - NTP_DELTA + fractional)

    def _string(self):
        end = self.packet.index('\x00', self.offset)
        value = self.packet[self.offset:end]
        self.offset = end + 1
        self._pad()
        return value

    def _blob(self):
        length = self._unpack('>i')
        value = self.packet[self.offset:(self.offset + length)]
        self.offset += length
        self._pad()
        return Blob(value)

    def read(self):
        address = self._string()
        if address == '#bundle':
            timetag = self._time()
            elements = []
            while self.offset < len(self.packet):
                maxoffset = self._int() + self.offset
                elements.append(self.read())
                if self.offset > maxoffset:
                    raise Exception("Invalid bundle. Offset was %s while expected <= %s", self.offset, maxoffset)
            return Bundle(timetag, *elements)

        typetags = self._string()
        if not typetags.startswith(','):
            raise Exception('Invalid message')
        return Message(address, *[self.tag_mapping[typetag](self) for typetag in typetags[1:]])

    tag_mapping = {'i': _int, 'f': _float, "N": _null, 't': _time, 's': _string, 'b': _blob}


def deserialize(packet):
    return DeserializerStream(packet).read()


class Client(object):
    def __init__(self, address):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.connect(address)

    def send(self, message):
        self.socket.send(serialize(message))


class Server(object):
    def __init__(self, address, handler, serverclass = SocketServer.ThreadingUDPServer):
        class Unbundler(SocketServer.DatagramRequestHandler):
            def handle(self):
                self.handle_element(deserialize(self.packet))

            def handle_element(self, element):
                if isinstance(element, Message):
                    handler(element, self.client_address)
                    return 
                diff = element.timetag - time.time()
                if diff > 0:
                    time.sleep(diff)
                for subelement in element.elements:
                    self.handle_element(subelement)

        self.server = serverclass(address, Unbundler)
        self.handler = handler

    def handle(self, message, client_address):
        # TODO: Handle patterns
        pattern = message.address
        self.handler(message, client_address)

    def serve_forever(self):
        self.server.serve_forever()


def test():
    serialized = '#bundle\x00\x83\xaa~\xfb\x00\x00\x00\x00\x00\x00\x000/abcd/defg/\x00,ifstb\x00\x00\x00\x00\x00\x01@\x00\x00\x003\x00\x00\x00\x83\xaa~\x84\x80\x00\x00\x00\x00\x00\x00\x0267\x00\x00'
    message = Bundle(Time(123), Message("/abcd/defg/", 1, 2.0, "3", Time(4.5), Blob("67")))
    assert serialize(message) == serialized
    assert deserialize(serialized) == message
    
if __name__ == "__main__":
    test()