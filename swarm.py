#Using bluetooth to control multiple xrp robots through an app.

import bluetooth
import io
import os
import micropython
from micropython import const
import machine
from XRPLib.defaults import *

#IRQ events
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


#Flags
_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

#Advertisement stuff
_ADV_IND = const(0x00)
_ADV_DIRECT_IND = const(0x01)
_ADV_SCAN_IND = const(0x02)
_ADV_NONCONN_IND = const(0x03)
_SCAN_RSP = const(0x04)

#UART: Way of transmitting data between bluetooth devices
_UUID = bluetooth.UUID("51ff9301-d04e-4a0d-91c9-975fca9cdf95")
_NAME = (
    bluetooth.UUID("cf556646-2b41-4888-9e6a-ea97d6b37175"),
    _FLAG_READ | _FLAG_NOTIFY
)
_COMMAND = (
    bluetooth.UUID("ed59696a-b609-4cea-a09a-5885cce3c5ca"),
    _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE
)
_SERVICE = (
    _UUID,
    (_NAME, _COMMAND)
)
class SwarmAgent:
    def __init__(self, p_name, p_children=False):
        self.name=p_name[:8]
        self.children=p_children
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self.periodic)
        ((self._tname, self._command),) = self._ble.gatts_register_services((_SERVICE,))
        self.parent_handle=""
        self.connected_children=set()
        self.next_action=False
        print("Advertising")
        self._ble.gap_advertise(500000,) #TODO: Add correct parameters for gap_advertise. These include the interval and a payload.
    def periodic(self, event, data):
        #These events are for interactions between the device and its parent
        if(event==_IRQ_CENTRAL_CONNECT):
            # A central has connected to this peripheral.
            conn_handle, addr_type, addr = data
            print("Connected to device:" + conn_handle)
            self._ble.gap_advertise(0)
            parent_handle=conn_handle
            pass
        elif(event==_IRQ_CENTRAL_DISCONNECT):
            # A central has disconnected from this peripheral.
            conn_handle, addr_type, addr = data
            print("Disconnected from parent")
            parent_handle=""
            pass
        elif event == _IRQ_GATTS_WRITE:
            # A client has written to this characteristic or descriptor.
            conn_handle, value_handle = data
            if value_handle==self._tname and self._ble.gatts_read(self._tname).decode('utf-8')==self.name:
                self.next_action=True
                # If the value written is the target name, and the name matches the robot's name, a variable to check
                # if the robot does the next command is set to be true
            elif value_handle==self._command:
                # The following if statement checks if the robot should follow the given command
                if self.next_action:
                    self.next_action=False
                    commands=self._ble.gatts_read(self._command)
                    if(commands[0]==0):
                        drivetrain.turn(commands[1])
                    else:
                        drivetrain.turn(-commands[1])
                    commands=commands[2:]
                    drive_distance=0
                    for i in range(len(commands)):
                        drive_distance+= #TODO: need to convert base 256 to base 10
                        pass
                    drivetrain.straight(drive_distance)
                    # If it should, it reads the command from the central device. commands[0] dictates if the turn value is negative
                    # commands[1] is the amount of turn degrees. commands[2] and onward
                else:
                    for connection in self.connected_children:
                        self._ble.gattc_write(connection, self._tname, self._ble.gatts_read(self._tname))
        elif event == _IRQ_GATTC_WRITE_DONE:
        # A gattc_write() has completed.
        # Note: Status will be zero on success, implementation-specific value otherwise.
            conn_handle, value_handle, status = data
            if value_handle==self._tname:
                self._ble.gattc_write(conn_handle, self._command, self._ble.gatts_read(self._command))#TODO: Figure out what data to be passed into this function. Assuming the command
                                                         # is going to be added to a parameter?

        #An event for scanning for devices to connect
        elif(event==_IRQ_SCAN_RESULT):
            # A single scan result.
            addr_type, addr, adv_type, rssi, adv_data = data
            pass

            
    def connected_to_central(self) -> bool:
        return len(self.parent_handle)>0
    
    
    




