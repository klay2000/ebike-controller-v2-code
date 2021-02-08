from machine import I2C, Pin

from Device import Device

I2C_FREQ = 1000

if __name__ == '__main__':
    i2c = I2C(sda=Pin(21), scl=Pin(22), freq=I2C_FREQ)
    device_ids = i2c.scan()

    devices = []

    for i in device_ids:
        devices.append(Device(i2c, i))


# def loadData():
#
#
# def readDevices():
#
#
# def checkDevices():
#
