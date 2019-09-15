import time
import socket
import threading
import socketserver
from traceback import format_exc

from abc import ABCMeta, abstractmethod

from ae.core import DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE, po

# import time         # needed only for testing

TCP_CONNECTION_BROKEN_MSG = "socket connection broken!"

TCP_MAXBUFLEN = 8192
TCP_END_OF_MSG_CHAR = b'\x04'

DEBUG_RUNNING_CHARS = "|/-\\"


# server infrastructure

class RequestXmlHandler(socketserver.BaseRequestHandler, metaclass=ABCMeta):
    error_message = ""

    """
    def setup(self):
        # the socket is called request in the request handler
        self.request.settimeout(1.0)
        #self.request.setblocking(False)
    """

    def notify(self):
        po("****  " + self.error_message)

    def handle(self):
        xml_recv = b""
        try:
            while xml_recv[-1:] != TCP_END_OF_MSG_CHAR:
                chunk = self.request.recv(TCP_MAXBUFLEN)
                if not chunk:  # socket connection broken, see https://docs.python.org/3/howto/sockets.html#socket-howto
                    self.error_message = "RequestXmlHandler.handle(): " + TCP_CONNECTION_BROKEN_MSG
                    self.notify()
                    return
                xml_recv += chunk
            xml_recv = xml_recv[:-1]        # remove TCP_END_OF_MSG_CHAR
            resp = self.handle_xml(xml_recv) + TCP_END_OF_MSG_CHAR
            self.request.sendall(resp)

        except Exception as ex:
            self.error_message = "RequestXmlHandler.handle() exception='" + str(ex) + "' (XML=" + str(xml_recv) + ")"\
                                 + "\n" + format_exc()
            self.notify()

    @abstractmethod
    def handle_xml(self, xml_from_client):
        pass


class _ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class TcpServer:

    def __init__(self, ip, port, cls_xml_handler, debug_level=DEBUG_LEVEL_DISABLED):
        self.debug_level = debug_level
        # cls_xml_handler is a RequestXmlHandler subclass with an overridden handle_xml() method
        server = _ThreadedServer((ip, port), cls_xml_handler)

        if debug_level >= DEBUG_LEVEL_VERBOSE:
            po("TcpServer initialized on ip/port: ", server.server_address)

        # start a thread with the server - which then start one more thread for each request/client-socket
        server_thread = threading.Thread(target=server.serve_forever)
        # exit server thread when main tread terminates
        server_thread.daemon = True
        server_thread.start()

        if debug_level >= DEBUG_LEVEL_VERBOSE:
            po("TcpServer running in thread:", server_thread.name)

        self.server = server

    def run(self, display_animation=False):
        try:
            sleep_time = 0.5 / len(DEBUG_RUNNING_CHARS)
            index = 0
            while True:
                if display_animation:
                    index = (index + 1) % len(DEBUG_RUNNING_CHARS)
                    po("Server is running " + DEBUG_RUNNING_CHARS[index], end="\r", flush=True)
                time.sleep(sleep_time)
        except Exception as ex:
            po("Server killed with exception: ", ex)
            if self.debug_level:
                po(format_exc())
        self.server.shutdown()
        self.server.server_close()


# client infrastructure

class TcpClient:
    error_message = ""
    received_xml = ""

    def __init__(self, server_ip, server_port, timeout=3.6, encoding='utf8', debug_level=DEBUG_LEVEL_DISABLED):
        super(TcpClient, self).__init__()
        self.serverIP = server_ip
        self.serverPort = server_port
        self.timeout = timeout
        self.encoding = encoding
        self.debug_level = debug_level

    def send_to_server(self, xml):
        self.error_message = ""
        self.received_xml = ""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if self.debug_level >= DEBUG_LEVEL_VERBOSE:
                    po("TcpClient connecting to server ", self.serverIP, " on port ", self.serverPort,
                           " with encoding", self.encoding, " and timeout", self.timeout)
                # adding sock.setblocking(0) is resulting in a BlockingIOError exception
                sock.settimeout(self.timeout)
                sock.connect((self.serverIP, self.serverPort))
                bs = bytes(xml, encoding=self.encoding, errors='backslashreplace' if self.debug_level else 'ignore')
                sock.sendall(bs + TCP_END_OF_MSG_CHAR)
                self.received_xml = self._receive_response(sock)
        except Exception as ex:
            self.error_message = "TcpClient.send_to_server() exception: " + str(ex) \
                + (" (sent XML=" + xml + ")" + "\n" + format_exc() if self.debug_level >= DEBUG_LEVEL_VERBOSE else "")

        return self.error_message

    def _receive_response(self, sock):
        def _handle_err_gracefully(extra_msg=""):
            # socket connection broken, see https://docs.python.org/3/howto/sockets.html#socket-howto
            # .. and for 100054 see https://stackoverflow.com/questions/35542404
            self.error_message = "TcpClient._receive_response(): " + TCP_CONNECTION_BROKEN_MSG + extra_msg
            if self.debug_level:
                po(self.error_message)
        xml_recv = b""
        try:
            while xml_recv[-1:] != TCP_END_OF_MSG_CHAR:
                chunk = sock.recv(TCP_MAXBUFLEN)
                if not chunk:
                    _handle_err_gracefully()
                    break
                xml_recv += chunk
            xml_recv = xml_recv[:-1]        # remove TCP_END_OF_MSG_CHAR

        except Exception as ex:
            if 10054 in ex.args:
                # [ErrNo|WinError 10054] An existing connection was forcibly closed by the remote host
                _handle_err_gracefully(" ErrNo=10054 (data loss is possible)")
            else:
                self.error_message = "TcpClient._receive_response() err: " + str(ex) \
                                     + (" (received XML=" + str(xml_recv, self.encoding) + ")" + "\n" + format_exc()
                                        if self.debug_level >= DEBUG_LEVEL_VERBOSE else "")

        return str(xml_recv, self.encoding)
