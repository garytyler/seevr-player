from array import array

from PyQt5.QtCore import QByteArray

from . import socks


class RemoteInputClient:
    def __init__(self, url):
        self.motion_state = None
        self.state_changed = False
        self.socket = socks.AutoConnectSocket()

        self._curr_motion_state = QByteArray()
        self._last_motion_state = QByteArray()

        self.socket.binaryMessageReceived.connect(self.received_bytes)

    def stop_connecting(self):
        self.socket.stop_attempting()

    def received_bytes(self, qbytearray):
        self._curr_motion_state = qbytearray

    def get_new_motion_state(self):
        if self._curr_motion_state == self._last_motion_state:
            return
        motion_state_array = array("d", self._curr_motion_state.data())
        return motion_state_array
