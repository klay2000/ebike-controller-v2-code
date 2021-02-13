from machine import I2C, Pin, light_sleep
from Device import Device
from types import Boolean
import ujson

I2C_FREQ = 1000
DATA_FILE_NAME = 'data.json'
SYNC_TIME = 5000

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

# Returns an available id on success, -1 on fail.
def prepare_to_sync_device(i2c, devices):

    # Fail if there is no more space for devices, this will be 120 because 128 max devices with 8 reserved device
    # addresses makes 120, odds are nobody's crazy enough to hit this though ;).
    if len(devices) > 120:
        return -1

    ids = i2c.scan()

    used_ids = []

    for i in devices:
        used_ids.append(i.dev_id)

    used_ids = sorted(used_ids)

    available_id = -1

    last_id = used_ids[0]

    # Search through for an unused id before tacking it on the end for the sake of cleanliness.
    for i in used_ids:
        if i-last_id > 1:
            available_id = i+1
            break

        last_id = i

    if available_id == -1:
        available_id = used_ids[len(used_ids)]+1

    # set all device's sync bits high in preparation
    for i in ids:
        i2c.writeto_mem(i, 0x06, 0xFF)

    return available_id

# Returns new device, if a new device isn't created returns -1.
def sync_device(i2c, id_to_use):
    ids = i2c.scan()

    for i in ids:
        if not Boolean.convert(i2c.readfrom_mem(i, 0x06, Boolean.length)):
            return Device(i2c, i)
    return -1

if __name__ == '__main__':
    i2c = I2C(sda=Pin(21), scl=Pin(22), freq=I2C_FREQ)

    data = get_saved_data(i2c)

    devices = data[0]
    connections = data[1]

