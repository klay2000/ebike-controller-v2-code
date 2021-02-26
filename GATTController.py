# This file is adapted from the Nordic Uart Service example on the Micropython git repository.

import bluetooth
from BLEAdvertising import advertising_payload
import ujson
from micropython import const

EVENT_SYNC = const(0)
EVENT_CONNECTION_MODIFY = const(1)
EVENT_DEVICE_MODIFY = const(2)
EVENT_REQUEST_DEVICES = const(3)

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

_FLAG_READ = const(0x0002)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

_BIKE_UUID = bluetooth.UUID("2389edba-6af5-420b-9457-079d7f29af73")
_DEVICES = (
    bluetooth.UUID("53055a92-931f-40c5-b352-af50cf71262b"),
    _FLAG_READ,
)
_SYNC_MODE = (
    bluetooth.UUID("64534edd-53ab-4b5c-8a9b-3a367f8177c6"),
    _FLAG_WRITE,
)
_CHANNEL_IDS = (
    bluetooth.UUID("53e5e22d-61b6-4da2-84ab-048454c8263e"),
    _FLAG_READ | _FLAG_WRITE,
)
_DATA = (
    bluetooth.UUID("7e5b558e-c8fd-4a94-be1d-e133a465f3cd"),
    _FLAG_READ | _FLAG_NOTIFY,
)
_MODIFY_CONNECTIONS = (
    bluetooth.UUID("ab217364-5a41-4bb8-b8b7-9534f07ce560"),
    _FLAG_WRITE,
)
_MODIFY_DEVICES = (
    bluetooth.UUID("2d059e49-2b21-4055-951b-7fc370b4312d"),
    _FLAG_WRITE,
)
_BIKE_SERVICE = (
    _BIKE_UUID,
    (_DEVICES, _SYNC_MODE, _CHANNEL_IDS, _DATA, _MODIFY_CONNECTIONS, _MODIFY_DEVICES),
)

# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_GENERIC_CYCLING = const(1152)


class GATTController:
    def __init__(self, ble, name="EBike-Controller"):
        self._ble = ble             # save instance of ble
        self._ble.active(True)      # set ble to active
        self._ble.irq(self._irq)    # set ble irq to _irq
        # register service
        ((self._channels_handle,
          self._sync_handle,
          self._channel_ids_handle,
          self._data_handle,
          self._modify_con_handle,
          self._modify_dev_handle),) = self._ble.gatts_register_services((_BIKE_SERVICE,))
        self._handler = None
        # set advertising payload
        self._payload = advertising_payload(name=name, appearance=_ADV_APPEARANCE_GENERIC_CYCLING)
        self._advertise()   # start advertising
        self._connection = None

    def irq(self, handler):
        self._handler = handler
        self._handler(EVENT_REQUEST_DEVICES, None, self)

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connection = conn_handle
            self._stop_advertising()
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if self._handler:
                if value_handle == self._sync_handle:
                    self._handler(EVENT_SYNC, self._ble.gatts_read(value_handle), self)
                elif value_handle == self._modify_con_handle:
                    self._handler(EVENT_CONNECTION_MODIFY, self._ble.gatts_read(self._modify_con_handle), self)
                    self._handler(EVENT_REQUEST_DEVICES, None, self)
                elif value_handle == self._modify_dev_handle:
                    self._handler(EVENT_DEVICE_MODIFY, self._ble.gatts_read(self._modify_dev_handle), self)
                    self._handler(EVENT_REQUEST_DEVICES, None, self)

    def write_data(self, data):
        if self._connection is not None:
            self._ble.gatts_notify(self._connection, self._data_handle, data)

    def update_devices(self, devices):
        # convert data
        device_dicts = []

        for i in devices:
            device_dicts.append(i.to_dict())

        data = {"devices": device_dicts}

        self._ble.gatts_write(self._channels_handle, ujson.dumps(data))

    def close(self):
        self._ble.gap_disconnect(self._connection)

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)

    def _stop_advertising(self):
        self._ble.gap_advertise(None)


def demo():
    import time

    ble = bluetooth.BLE()
    uart = GATTController(ble)

    def on_rx(event_code, data):
        print(event_code)
        print(data)

    uart.irq(handler=on_rx)
    nums = [4, 8, 15, 16, 23, 42]
    i = 0

    try:
        while True:
            uart.write_data(str(nums[i]) + "\n")
            i = (i + 1) % len(nums)
            time.sleep_ms(1000)
    except KeyboardInterrupt:
        pass

    uart.close()
