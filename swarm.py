"""
MIT License

Copyright (c) 2024 https://github.com/Advay17

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
#Using bluetooth to control multiple xrp robots through an app.
#The program utilizes Piconet topology(a type of tree), where one central device can connect to various central-peripheral devices. These devices then connect to other central-peripheral or peripheral devices.
#The central device sends instructions to each connected device. If the connected device is the device the instructions are intended for, it follows them and notifies the central device upon completion.
#Otherwise, it sends the data to any and all connected child devices.
import bluetooth
import io
import os
import micropython
import machine
from XRPLib.defaults import *
import math
import struct

#region IRQ events
#These are the different events that can occur when using bluetooth. When one is triggered, the event function runs with the specific event type, along with event specific data.
#Specific information is listed in the event function under each event.
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(13)
_IRQ_GATTC_DESCRIPTOR_DONE = const(14)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)
_IRQ_GATTC_INDICATE = const(19)
_IRQ_GATTS_INDICATE_DONE = const(20)
_IRQ_MTU_EXCHANGED = const(21)
_IRQ_L2CAP_ACCEPT = const(22)
_IRQ_L2CAP_CONNECT = const(23)
_IRQ_L2CAP_DISCONNECT = const(24)
_IRQ_L2CAP_RECV = const(25)
_IRQ_L2CAP_SEND_READY = const(26)
_IRQ_CONNECTION_UPDATE = const(27)
_IRQ_ENCRYPTION_UPDATE = const(28)
_IRQ_GET_SECRET = const(29)
_IRQ_SET_SECRET = const(30)
#endregion

#region Flags
#Some of the different flags that determine the behavior of the service
_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
#endregion

#region Advertisement stuff
#Different constants which are useful for the advertising payload function
_ADV_IND = const(0x00)
_ADV_DIRECT_IND = const(0x01)
_ADV_SCAN_IND = const(0x02)
_ADV_NONCONN_IND = const(0x03)
_SCAN_RSP = const(0x04)
_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x3)
_ADV_TYPE_UUID32_COMPLETE = const(0x5)
_ADV_TYPE_UUID128_COMPLETE = const(0x7)
_ADV_TYPE_UUID16_MORE = const(0x2)
_ADV_TYPE_UUID32_MORE = const(0x4)
_ADV_TYPE_UUID128_MORE = const(0x6)
_ADV_TYPE_APPEARANCE = const(0x19)

_ADV_MAX_PAYLOAD = const(31)
#endregion

#region Main Service
#A peripheral bluetooth device has one or more different "services", each of which contains different characterisitcs. Each characteristic allows for the transmission of a byte
#array of data. This program just uses 1 service. UART style communication was considered, but it overcomplicated the transmission of data, so just one service was used.

#The UUID is the unique bluetooth identifier of the program.
_UUID = bluetooth.UUID("51ff9301-d04e-4a0d-91c9-975fca9cdf95")
#_COMMAND is the bluetooth characteristic used to transfer data. It is a 2 element tuple containing the characteristic's unique ID and a set of flags that show the behaviors
#the command uses, combined by a bitwise or. _COMMAND transfers the following data in the following order:
_COMMAND = (
    bluetooth.UUID("ed59696a-b609-4cea-a09a-5885cce3c5ca"),
    _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE
)
#The service is the sole service this program uses. It is a tuple of it's UUID and the sole characteristic, _COMMAND. By writing to this service from the site, a 5 element
#byte array is transmitted to the XRP. The elements are as follows:
#0:Number of the XRP: Should be unique(unless the user wishes for multiple XRPs to follow the commands to 1 number, that would be interesting)
#1:Whether the turn is to the left or to the right. If it is 0, the XRP turns to the left, else to the right.
#2:Degrees the XRP turns. Technically, the limit is 255 degrees, but the site will only send up to 180 degrees.
#3:Meters the XRP travels, to a maximum of 255, as any amount after that may violate the geneva convention
#4:Centimeters the XRP travels, to a maximum of 255, but practically capped at 99 due to conversion to meters.
_SERVICE = (
    _UUID,
    (_COMMAND,)
)
#endregion

#region Supporting Methods
#Methods copied from https://github.com/micropython/micropython/blob/master/examples/bluetooth/ble_advertising.py to allow for bluetooth advertising.
# Generate a payload to be passed to gap_advertise(adv_data=...).
def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
    payload = bytearray()

    def _append(adv_type, value):
        nonlocal payload
        payload += struct.pack("BB", len(value) + 1, adv_type) + value

    _append(
        _ADV_TYPE_FLAGS,
        struct.pack("B", (0x01 if limited_disc else 0x02) + (0x18 if br_edr else 0x04)),
    )

    if name:
        _append(_ADV_TYPE_NAME, name)

    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(_ADV_TYPE_UUID16_COMPLETE, b)
            elif len(b) == 4:
                _append(_ADV_TYPE_UUID32_COMPLETE, b)
            elif len(b) == 16:
                _append(_ADV_TYPE_UUID128_COMPLETE, b)

    # See org.bluetooth.characteristic.gap.appearance.xml
    if appearance:
        _append(_ADV_TYPE_APPEARANCE, struct.pack("<h", appearance))

    if len(payload) > _ADV_MAX_PAYLOAD:
        raise ValueError("advertising payload too large")

    return payload


def decode_field(payload, adv_type):
    i = 0
    result = []
    while i + 1 < len(payload):
        if payload[i + 1] == adv_type:
            result.append(payload[i + 2 : i + payload[i] + 1])
        i += 1 + payload[i]
    return result


def decode_name(payload):
    n = decode_field(payload, _ADV_TYPE_NAME)
    return str(n[0], "utf-8") if n else ""


def decode_services(payload):
    services = []
    for u in decode_field(payload, _ADV_TYPE_UUID16_COMPLETE):
        services.append(bluetooth.UUID(struct.unpack("<h", u)[0]))
    for u in decode_field(payload, _ADV_TYPE_UUID32_COMPLETE):
        services.append(bluetooth.UUID(struct.unpack("<d", u)[0]))
    for u in decode_field(payload, _ADV_TYPE_UUID128_COMPLETE):
        services.append(bluetooth.UUID(u))
    return services
#endregion
class SwarmAgent:
    def __init__(self, p_number, p_children=False):
        #Numeric identifier of the XRP, ranging from 0-255. Should be unique, unless the user wishes multiple XRPs to be controlled by one icon.
        self.number=p_number

        #Whether or not the XRP will connect to other XRPs
        self.children=p_children

        #Bluetooth activation
        self._ble = bluetooth.BLE()
        self._ble.active(True)

        #Sets the event function to event()
        self._ble.irq(self.event)

        #Sets _command to be the registered service
        ((self._command,),) = self._ble.gatts_register_services((_SERVICE,))

        #Parent handle, that is set to whatever the handle is when the parent connects
        self.parent_handle=""
        
        #A set of all the connected child XRPs
        self.connected_children=set()
        
        #Starts advertising the XRP
        print("Advertising")
        self._ble.gap_advertise(500000, advertising_payload(name=str(self.number), services=[_UUID])) #TODO: Add correct parameters for gap_advertise. These include the interval and a payload.
        imu.reset()
    
    #This function runs every time an event occurs, having a parameter for the type of the event and the data the event contains
    def event(self, event, data):
        #These events are for interactions between the device and its parent
        if event==_IRQ_CENTRAL_CONNECT:
            # A central device has connected to this peripheral.
            conn_handle, addr_type, addr = data
            print("Connected to device:" + conn_handle)
            #Stops advertising so that it doesn't accidentally join another XRP
            self._ble.gap_advertise(None)
            parent_handle=conn_handle
            if self.children==True and len(self.connected_children)<6:
                #If the XRP can have other XRPs and it has less than six connected XRPs(this amount needs to be lowered after testing to see efficiency), the XRP begins to scan for other bluetooth devices for an indefinite period of time
                self._ble.gap_scan(0)
            pass
        elif event==_IRQ_CENTRAL_DISCONNECT:
            # A central has disconnected from this peripheral.
            conn_handle, addr_type, addr = data
            print("Disconnected from parent")
            parent_handle=""
            #Reset parent handle
            pass
        elif event == _IRQ_GATTS_WRITE:
            # A client has written to this characteristic or descriptor.
            #This runs when the parent sends data to the child.
            conn_handle, value_handle = data
            #Reads the data
            commands=self._ble.gatts_read(self._command)
            if commands[0]==self.number:
                #If the XRP is the intended recipient, the commands are followed
                if(commands[1]==0):
                    #If the value is 0, the XRP turns left
                    drivetrain.turn(commands[2]) # type: ignore
                else:
                    #Else it turns right
                    drivetrain.turn(-commands[2]) # type: ignore
                #The XRP drives straight for commands[3] meters and commands[4] centimeters
                drivetrain.straight(commands[3]*100+commands[4]) # type: ignore
                #The XRP notifies its parent
                self._ble.gatts_notify(parent_handle, self._command, bytearray(self.number.to_bytes(1, 'big')))
                # If it should, it reads the command from the central device.
            else:
                #If the XRP is not the intended recipient, the children are sent the data
                for connection in self.connected_children:
                    self._ble.gattc_write(connection, self._command, commands)
        
        #Events for scanning for devices to connect
        elif event==_IRQ_SCAN_RESULT:
            # A single scan result.
            #The XRP found a bluetooth device(not confirmed if it is an XRP)
            addr_type, addr, adv_type, rssi, adv_data = data
            if adv_type in (_ADV_IND, _ADV_DIRECT_IND) and _UUID in decode_services(adv_data):
                #The XRP connects to the device if it is an XRP
                self._ble.gap_connect(addr_type, addr)
                pass
        elif event == _IRQ_PERIPHERAL_CONNECT:
            # A successful gap_connect().
            # The connection handle is added to the XRP's set and if the XRP has 6 children, it stops scanning for bluetooth devices.
            conn_handle, addr_type, addr = data
            self.connected_children.add(conn_handle)
            print("A child has connected:" + conn_handle)
            if len(self.connected_children)==6:
                self._ble.gap_scan(None)

        #Event for when a child disconnects
        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            # Connected peripheral has disconnected.
            # The child is removed from the set of children
            conn_handle, addr_type, addr = data
            self.connected_children.remove(conn_handle)
            print("A child has disconnected")
        
        #Event for when a child writes to the parent
        elif event==_IRQ_GATTC_NOTIFY:
            # A server has sent a notify request.
            conn_handle, value_handle, notify_data = data
            #The XRP notifies its parent, until the notification reaches the central device
            self._ble.gatts_notify(parent_handle, value_handle, notify_data)
            
    #checks if device is connected to parent   
    def connected_to_central(self) -> bool:
        return len(self.parent_handle)>0