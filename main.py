from machine import I2C, Pin
from Device import Device
import Bluetooth
from types import Boolean
import ujson

I2C_FREQ = 1000
DATA_FILE_NAME = 'data.json'
SYNC_TIME = 5000


def get_saved_data(i2c_obj):
    f = open(DATA_FILE_NAME, '+')
    data = f.read()
    if len(data) == 0:
        data = ujson.dumps({"devices": []})
        f.write(data)
        f.flush()

    f.close()

    data_dict = ujson.loads(data)

    read_devices = []

    for i in data_dict["devices"]:
        read_devices.append(Device.from_dict(i2c_obj, i))

    return read_devices


def write_new_data(new_devices):
    # convert data
    device_dicts = []

    connection_dicts = []

    for i in new_devices:
        device_dicts.append(i.to_dict())

    data = {"devices": device_dicts}

    # clear file
    open(DATA_FILE_NAME, "w").close()

    # write new data
    f = open(DATA_FILE_NAME, "+")
    f.write(ujson.dumps(data))
    f.flush()
    f.close()


# Returns an available id on success, -1 on fail.
def prepare_to_sync_device(i2c, devices):
    # Fail if there is no more space for devices, this will be 111 because scan only reads to 119, and 8 reserved device
    # addresses makes 120, odds are nobody's crazy enough to hit this though ;).
    if len(devices) > 111:
        return -1

    ids = i2c.scan()

    used_ids = []

    for i in devices:
        used_ids.append(i.dev_id)

    used_ids = sorted(used_ids)

    lowest_available_id = 9

    for i in used_ids:
        if i == lowest_available_id:
            lowest_available_id += 1
        if i > lowest_available_id:
            break

    # set all device's sync bits high in preparation
    for i in ids:
        i2c.writeto_mem(i, 0x06, b'\xff')

    return lowest_available_id


# Returns new device, if a new device isn't created returns -1.
def sync_device(i2c, id_to_use):
    ids = i2c.scan()

    for i in ids:
        i2c.writeto_mem(i, 0x00, bytearray([id_to_use]))

    return Device(i2c, id_to_use)


# Returns a reference to a channel from a tuple of (dev_id,channel_addr), returns None if none exists.
def get_channel_from_id_tuple(channel, devices):
    for i in devices:
        if i.dev_id == channel[0]:
            for j in i.channels:
                if j.address == channel[1]:
                    return j
    return None


# Updates values for each channel of each device
def update_channels(devices):
    for i in devices:
        for j in i.channels:
            if j.source_channel[0] != -1:
                if j.source_reference is None:
                    j.source_reference = get_channel_from_id_tuple(j.source_channel, devices)

                j.write_value(j.source_reference.read_value())


if __name__ == '__main__':
    i2c = I2C(sda=Pin(21), scl=Pin(22), freq=I2C_FREQ)

    devices = get_saved_data(i2c)

    # while True:
        # update_channels(devices)

