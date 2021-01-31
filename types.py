import struct


class Datatype:

    length = 0

    def toBytes(self, data):
        return 0

    def convert(self, data):
        return 0


class Uint8(Datatype):

    length = 1

    def toBytes(self, data):
        super().toBytes(data)

        return data.to_bytes(1, 'little')

    def convert(self, data):
        super().convert(data)

        return data


class Uint16(Datatype):

    length = 2

    def toBytes(self, data):
        super().toBytes(data)

        print(data.to_bytes(2, 'little'))

        return data.to_bytes(2, 'little')

    def convert(self, data):
        super().convert(data)

        return int.from_bytes(data, 'little')


class Float32(Datatype):

    length = 4

    def toBytes(self, data):
        super().toBytes(data);

        return struct.pack('f', data)

    def convert(self, data):
        super().convert(data)

        return struct.unpack('<f', data)


class String20(Datatype):

    length = 20

    def toBytes(self, data):
        super().toBytes(data)

        bytes = data.encode(encodeing='ascii', errors='replace')

        return bytes

    def convert(self, data):
        super().convert(data)

        result = ""

        for i in data[0:20]:
            if i == 0xFF:
                break
            result += chr(i)

        return result


class Boolean(Datatype):

    length = 1

    def toBytes(self, data):
        super().toBytes(data)

        return data.toBytes(1, 'little')

    def convert(self, data):
        super().convert(data)

        return not(data == 0)


def type_from_id(type_id):
    type_dict = {
        0x00: Uint8,
        0x01: Uint16,
        0x02: Float32,
        0x03: String20,
        0x04: Boolean
    }

    return type_dict[type_id]
