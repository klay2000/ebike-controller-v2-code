from types import *


class Channel:
    def __init__(self, dev_id, address, writable, datatype, label, i2c):
        self.dev_id = dev_id
        self.address = address
        self.writable = writable
        self.datatype = datatype
        self.label = label
        self.i2c = i2c

    def read_value(self):
        return self.datatype.convert(self.i2c.readfrom_mem(self.dev_id, self.address, self.datatype.length))

    def write_value(self, data):
        self.i2c.writeto_mem(self.dev_id, self.address, data)


class Device:
    def __init__(self, i2c, dev_id):
        self.i2c = i2c
        self.dev_id = dev_id
        self.channels = []
        self.name = String20().convert(self.i2c.readfrom_mem(self.dev_id, 0x01, String20().length))
        self.scan_channels()

    def scan_channels(self):
        channels_len = Uint8().convert(self.i2c.readfrom_mem(self.dev_id, 0x02, 1)[0])
        writable = self.i2c.readfrom_mem(self.dev_id, 0x04, channels_len * Boolean().length)
        types = self.i2c.readfrom_mem(self.dev_id, 0x05, channels_len * Uint8().length)
        labels = self.i2c.readfrom_mem(self.dev_id, 0x03, channels_len * String20().length)

        for i in range(0, channels_len):
            self.channels.append(
                Channel(self.dev_id,
                        i + 0x10,  # Start numbering from 0x10 since the first 16 addresses are reserved.
                        Boolean().convert(writable[i]),
                        type_from_id(Uint8().convert(types[i]))(),
                        String20().convert(labels[i * 20:i * 20 + 20]),
                        self.i2c))
