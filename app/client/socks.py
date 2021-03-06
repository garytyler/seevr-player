import logging
from random import choice
from string import ascii_uppercase, digits

from PyQt5 import QtNetwork
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtWebSockets import QWebSocket, QWebSocketProtocol

log = logging.getLogger(__name__)


class ClientSocketBase(QWebSocket):
    def __init__(self):
        QWebSocket.__init__(
            self, origin="", version=QWebSocketProtocol.Version13, parent=None
        )
        # Connect base methods to signals
        self.connected.connect(self.__connected)
        self.disconnected.connect(self.__disconnected)

    def __connected(self):
        self.peeraddr = self.peerAddress().toString()
        log.info(f"CONNECTED peer_address={getattr(self, 'peeraddr', '')}")

    def __disconnected(self):
        log.info(f"DISCONNECTED peer_address={getattr(self, 'peeraddr', '')}")
        self.peeraddr = None

    def _pong(self, elapsed_time, payload):
        if not str(payload) == str(self.__payload):
            raise RuntimeError("Ping payload mismatch")
        else:
            print("pong time: {}".format(elapsed_time))
            self.__payload = None

    def send_ping(self):
        self.__payload = self.rand_id().encode()
        self.pong.connect(self._pong)
        self.ping(self.__payload)

    @staticmethod
    def rand_id(size=6):
        return "".join(choice(ascii_uppercase + digits) for _ in range(size))

    def state_str(self):
        if self.state() == QtNetwork.QAbstractSocket.BoundState:
            return "BoundState"
        if self.state() == QtNetwork.QAbstractSocket.ClosingState:
            return "ClosingState"
        if self.state() == QtNetwork.QAbstractSocket.ConnectedState:
            return "ConnectedState"
        if self.state() == QtNetwork.QAbstractSocket.ConnectingState:
            return "ConnectingState"
        if self.state() == QtNetwork.QAbstractSocket.HostLookupState:
            return "HostLookupState"
        if self.state() == QtNetwork.QAbstractSocket.ListeningState:
            return "ListeningState"
        if self.state() == QtNetwork.QAbstractSocket.UnconnectedState:
            return "UnconnectedState"


class AutoReconnectSocket(ClientSocketBase):

    ConnectedState = QtNetwork.QAbstractSocket.ConnectedState
    ConnectingState = QtNetwork.QAbstractSocket.ConnectingState
    UnconnectedState = QtNetwork.QAbstractSocket.UnconnectedState

    def __init__(self):
        ClientSocketBase.__init__(self)
        self.KeepAliveOption = True
        self.LowDelayOption = True

        self.__connection_expected = False

        self.qurl = QUrl()

        # Timer for connection attempts
        self.connect_timer = QTimer()
        self.connect_timer.setTimerType(Qt.VeryCoarseTimer)

        self.stateChanged.connect(self._on_state_changed)

    def _attempt_open(self):
        self.connect_timer.singleShot(0, lambda: self.open(self.qurl))
        log.info(f"SOCKET OPEN ATTEMPT qurl={self.qurl}")

    def _on_state_changed(self, state: QtNetwork.QAbstractSocket.SocketState):
        log.info(f"SOCKET STATE CHANGED state={self.state_str()} qurl={self.qurl}")
        if state == QtNetwork.QAbstractSocket.UnconnectedState:
            if self.__connection_expected:
                self._attempt_open()
        elif state == QtNetwork.QAbstractSocket.ConnectedState:
            self.__connection_expected = True

    def connect(self, url):
        self.qurl = QUrl(url)
        self._attempt_open()

    def disconnect(self):
        self.__connection_expected = False
        self.connect_timer.stop()
        self.close()
