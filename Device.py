from types import *


class Channel:
    def __init__(self, dev_id, address, writable, datatype, label, i2c, source_channel=(-1, -1)):
        self.dev_id = dev_id
        self.address = address
        self.writable = writable
        self.datatype = datatype
        self.label = label
        self.i2c = i2c
        self.source_channel = source_channel    # actually a tuple with (deviceID, ChannelAddr)
        self.source_reference = None            # a reference to the source channel

    @classmethod
    def from_dict(cls, dev_id, json_dict, i2c):
        return Channel(dev_id,
                       json_dict["address"],
                       json_dict["writable"],
                       type_from_id(json_dict["type"])(),
                       json_dict["label"],
                       i2c,
                       source_channel=json_dict["sourceChannel"])

    def read_value(self):
        return self.datatype.convert(self.i2c.readfrom_mem(self.dev_id, self.address, self.datatype.length))

    def write_value(self, data):
        self.i2c.writeto_mem(self.dev_id, self.address, self.datatype.toBytes(data))

    def get_source(self):
        return self.source_channel

    def to_dict(self):
        return {
            "address": self.address,
            "writable": self.writable,
            "type": self.datatype.id,
            "label": self.label,
            "sourceChannel": self.source_channel
        }


class Device:
    def __init__(self, i2c, dev_id, scan=True):
        self.i2c = i2c
        self.dev_id = dev_id
        self.name = ""
        self.channels = []
        if scan:
            self.name = String20().convert(self.i2c.readfrom_mem(self.dev_id, 0x01, String20().length))
            self.scan_channels()

    @classmethod
    def from_dict(cls, i2c, json_dict):
        dev = Device(i2c, json_dict["id"], scan=False)
        dev.name = json_dict["name"]
        for i in json_dict["channels"]:
            dev.channels.append(Channel.from_dict(dev.dev_id, i, i2c))
        return dev

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

    def to_dict(self):
        channel_dicts = []

        for i in self.channels:
            channel_dicts.append(i.to_dict())

        return {
            "id": self.dev_id,
            "name": self.name,
            "channels": channel_dicts
        }
