from machine import I2C, Pin, Timer
from Device import Device
import utime
import GATTController
import ubluetooth
from types import Boolean, Uint8
import ujson
from micropython import const

I2C_FREQ = const(1000)
DATA_FILE_NAME = 'data.json'

UPDATE_DELAY = const(100)

LOG_LEVEL = -1  # -1 is debug, 0 is logging, 1 is release, 2 is error only.

SYNC_TIME = const(10000)
DEVICE_SYNC_ATTEMPTS = 10

STATE_STARTING = const(0)
STATE_RUNNING = const(1)
STATE_SYNCING = const(2)

global system_state
system_state = STATE_STARTING

i2c = None
devices = []


def log(message, log_level=-1):
    if LOG_LEVEL <= log_level:
        if log_level == 2:
            print("Bruh, " + message + "!")
        if log_level == 1:
            print(message)
        if log_level == 0:
            print("Dude, " + message + ".")
        if log_level == -1:
            print("DEBUG: " + message)


def get_saved_data():
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
        read_devices.append(Device.from_dict(i2c, i))

    log("loaded old device data", log_level=0)

    return read_devices


def write_new_data():
    # convert data
    device_dicts = []

    for i in devices:
        device_dicts.append(i.to_dict())

    data = {"devices": device_dicts}

    # clear file
    open(DATA_FILE_NAME, "w").close()

    # write new data
    f = open(DATA_FILE_NAME, "+")
    f.write(ujson.dumps(data))
    f.flush()
    f.close()

    log("wrote new device data to memory", log_level=0)


def try_to_sync_device():
    global system_state

    # Fail if there is no more space for devices, this will be 111 because scan only reads to 119, and 8 reserved device
    # addresses makes 120, odds are nobody's crazy enough to hit this though ;).
    if len(devices) > 111:
        return

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

    system_state = STATE_SYNCING

    log("sync wait started", log_level=0)

    tim0 = Timer(0)
    tim0.init(period=SYNC_TIME, mode=Timer.ONE_SHOT, callback=lambda x: complete_device_sync(lowest_available_id))


def complete_device_sync(id_to_use):
    global system_state

    log("sync wait over", log_level=0)

    if system_state != STATE_SYNCING:
        return

    ids = i2c.scan()

    utime.sleep_ms(500)

    for i in ids:
        i2c.writeto_mem(i, 0x00, bytearray([id_to_use]))

    utime.sleep(3)   # give the peripheral awhile to set up on it's new id

    for n in range(DEVICE_SYNC_ATTEMPTS):
        try:
            devices.append(Device(i2c, id_to_use))
            break
        except OSError as exc:
            continue

    write_new_data()

    system_state = STATE_RUNNING
    log("done syncing", log_level=0)


# Returns a reference to a channel from a tuple of (dev_id,channel_addr), returns None if none exists.
def get_channel_from_coordinates(channel):
    for i in devices:
        if i.dev_id == channel[0]:
            for j in i.channels:
                if j.address == channel[1]:
                    return j
    return None


# Updates values for each channel of each device
def update_channels():
    for i in devices:
        try:
            for j in i.channels:
                if j.source_channel[0] != -1:
                    if j.source_reference is None:
                        j.source_reference = get_channel_from_coordinates(j.source_channel)

                    if j.source_reference is not None:
                        j.write_value(j.source_reference.read_value())

        except OSError as exp:
            log("updating a channel failed: " + str(exp), log_level=2)

    channels = []
    for i in gatt_controller.get_channel_coordinates_to_send():
        channels.append(get_channel_from_coordinates(i))

    gatt_controller.send_channel_data(channels)


# Callback for GATT write events
def gatt_callback(event, data, _ble):
    global system_state

    log("GATT callback invoked, hold on tight", log_level=0)

    if event == GATTController.EVENT_SYNC:

        data = Boolean().convert(data)

        if data is True and system_state == STATE_RUNNING:
            try_to_sync_device()
        elif data is False and system_state == STATE_SYNCING:
            system_state = STATE_RUNNING

    elif event == GATTController.EVENT_REQUEST_DEVICES:
        _ble.update_devices(devices)

    elif event == GATTController.EVENT_REQUEST_DATA:
        channels = []

        for i in _ble.get_channel_coordinates_to_send():
            channels.append(get_channel_from_coordinates(i))

        _ble.send_channel_data(channels)

    elif event == GATTController.EVENT_CONNECTION_MODIFY:
        op = Uint8().convert(data[0])
        src = (Uint8().convert(data[1]), Uint8().convert(data[2]))
        dest = (Uint8().convert(data[3]), Uint8().convert(data[4]))

        if op == 0xff:
            get_channel_from_coordinates(dest).source_channel = src
        elif op == 0x00:
            get_channel_from_coordinates(dest).source_channel = (-1, -1)

        write_new_data()

    elif event == GATTController.EVENT_DEVICE_MODIFY:
        op = Uint8().convert(data[0])
        dev = Uint8().convert(data[1])
        dev_type = Uint8().convert(data[2])

        if op == 0x00:
            for i in devices:
                if i.dev_id == dev:
                    devices.remove(i)
                    break

        # TODO: add soft devices

        write_new_data()

    elif event == GATTController.EVENT_CHANGE_SENT_DATA:
        _ble.update_channels_to_send(data.decode())

if __name__ == '__main__':
    start_time = utime.ticks_ms()

    i2c = I2C(0, sda=Pin(21), scl=Pin(22), freq=I2C_FREQ)

    devices = get_saved_data()

    ble = ubluetooth.BLE()
    gatt_controller = GATTController.GATTController(ble)

    gatt_controller.irq(gatt_callback)

    log("Startup successful in " + str(utime.ticks_ms() - start_time) + "ms, welcome!", log_level=1)
    system_state = STATE_RUNNING

    while True:
        update_channels()
        utime.sleep_ms(UPDATE_DELAY)

