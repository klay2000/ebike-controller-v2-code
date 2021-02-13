from machine import I2C, Pin
from Device import Device
import ujson

I2C_FREQ = 1000
DATA_FILE_NAME = 'data.json'

if __name__ == '__main__':
    i2c = I2C(sda=Pin(21), scl=Pin(22), freq=I2C_FREQ)
    device_ids = i2c.scan()

    devices = []

    for i in device_ids:
        devices.append(Device(i2c, i))


def get_saved_data(i2c_obj):
    f = open(DATA_FILE_NAME, '+')
    data = f.read()
    if len(data) == 0:
        data = ujson.dumps({"connections": [], "devices": []})
        f.write(data)
        f.flush()

    f.close()

    data_dict = ujson.loads(data)

    read_devices = []
    read_connections = []

    for i in data_dict["devices"]:
        read_devices.append(Device.from_dict(i2c_obj, i))

    # TODO: connection parsing

    return read_devices, read_connections


def write_new_data(new_devices, new_connections):
    # convert data
    device_dicts = []

    connection_dicts = []

    for i in new_devices:
        device_dicts.append(i.to_dict())

    # TODO: connection parsing

    data = {"connections": connection_dicts, "devices": device_dicts}

    # clear file
    open(DATA_FILE_NAME, "w").close()

    # write new data
    f = open(DATA_FILE_NAME, "+")
    f.write(ujson.dumps(data))
    f.flush()
    f.close()
