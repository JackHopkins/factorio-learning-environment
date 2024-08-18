"""RCON client for factorio servers"""
import functools
import socket

import construct

try:
    import anyio
except ImportError:
    ASYNC_AVAILABLE = False
else:
    ASYNC_AVAILABLE = True

PACKET_PARSER = construct.GreedyRange(
    construct.Prefixed(
        construct.Int32sl,
        construct.Struct(
            "id" / construct.Int32sl,
            "type" / construct.Int32sl,
            "body" / construct.CString("utf8"),
            construct.Default(construct.CString("utf8"), "")
        )
    )
)


class RCONBaseError(Exception):
    """Exception base for all exceptions in this library"""

class ClientBusy(RCONBaseError):
    """Client is already busy with another call"""
class InvalidPassword(RCONBaseError):
    """RCON password is incorrect"""
class InvalidResponse(RCONBaseError):
    """RCON server returned an unparsable response or one with an unknown ID"""

class RCONNetworkError(RCONBaseError):
    """Base for all network related exceptions"""
class RCONNotConnected(RCONNetworkError):
    """Client is not connected to the RCON server"""
class RCONClosed(RCONNetworkError):
    """RCON server closed the connection"""
class RCONConnectError(RCONNetworkError):
    """Error connecting to the RCON server"""
class RCONSendError(RCONNetworkError):
    """Error sending data to the RCON server"""
class RCONReceiveError(RCONNetworkError):
    """Error receiving data from the RCON server"""

class RCONSharedBase:
    """Methods and data shared between both client classes"""
    def __init__(self):
        self.id_seq = 0
        self.socket_locked = False
        self.rcon_socket = None
        self.rcon_failure = False

    def get_id(self):
        """Gets an id for a command to be sent"""
        if self.id_seq == 2 ** 31 - 1: # signed int32 max
            self.id_seq = 0
        else:
            self.id_seq += 1
        return self.id_seq


def handle_socket_errors(alive_socket_required=True):
    """Socket error checking decorator"""
    def real_decorator(function):
        @functools.wraps(function)
        def wrapper(self, *args, **kwargs):
            if alive_socket_required:
                if self.rcon_socket is None:
                    raise RCONNotConnected(NOT_CONNECTED)
                if self.rcon_failure:
                    raise RCONNotConnected(RCON_FAILED)
                if self.socket_locked:
                    raise ClientBusy(CLIENT_BUSY)
            try:
                return function(self, *args, **kwargs)
            except BaseException:
                self.rcon_failure = True
                self.close()
                raise
            finally:
                self.socket_locked = False
        return wrapper
    return real_decorator


def async_handle_socket_errors(alive_socket_required=True):
    """Socket error checking decorator (async)"""
    def real_decorator(function):
        @functools.wraps(function)
        async def wrapper(self, *args, **kwargs):
            if alive_socket_required:
                if self.rcon_socket is None:
                    raise RCONNotConnected(NOT_CONNECTED)
                if self.rcon_failure:
                    raise RCONNotConnected(RCON_FAILED)
                if self.socket_locked:
                    raise ClientBusy(CLIENT_BUSY)
            try:
                return await function(self, *args, **kwargs)
            except BaseException:
                self.rcon_failure = True
                await self.close()
                raise
            finally:
                self.socket_locked = False
        return wrapper
    return real_decorator

class RCONClient(RCONSharedBase):
    """RCON client for factorio servers

    Params:
        ip_address: str; IP address to connect to.
        port: int; port to connect to.
        password: str; password to use to authenticate.
        timeout (optional, default None): float; timeout for socket operations.
        connect_on_init (optional, default True): bool; connect to the server when initialised.
    Raises:
        If connect_on_init is set, see RCONClient.connect().
        Else, no specific exceptions.
    Extra information:
        If any exception is raised (all stem from RCONBaseError) during operation,
        it is required that you reconnect to the RCON server (with .connect()).
        The server will not respond to any RCON requests if it is saving, so you should
        set a socket timeout if you are not prepared to wait a few seconds if the map is
        large or the server slow.
        A specified timeout of zero will disable any timeout rather than set non-blocking mode.
    """
    def __init__(self, ip_address, port, password, timeout=None, connect_on_init=True):
        super().__init__()
        self.timeout = timeout
        if timeout == 0:
            self.timeout = None
        self.ip_address = ip_address
        self.port = port
        self.password = password
        if connect_on_init:
            self.connect()

    @handle_socket_errors(alive_socket_required=False)
    def connect(self):
        """Connects to the RCON server

        Params:
            No params.
        Raises:
            RCONConnectError: if there is an error connecting to the server.
            InvalidPassword: if the password is incorrect.
            InvalidResponse: if the server returns an invalid response.
        Returns:
            Nothing returned.
        Extra information:
            Use this function to reconnect to the RCON server after an error.
        """
        self.close()
        self.rcon_failure = False
        self.rcon_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rcon_socket.settimeout(self.timeout)
        try:
            self.rcon_socket.connect((self.ip_address, self.port))
        except Exception as exc:
            raise RCONConnectError(CONNECT_SOCKET_ERROR) from exc
        self.id_seq = 0
        try:
            self.send_packet(0, 3, self.password)
            responses = self.receive_packets()
        except RCONBaseError as exc:
            raise RCONConnectError(CONNECT_COMMUNICATION_ERROR) from exc
        for response in responses:
            if response.type == 2:
                if response.id == -1:
                    raise InvalidPassword(INVALID_PASS)
                break
        else:
            raise InvalidResponse(INVALID_ID)

    def close(self):
        """Closes the connection to the RCON server

        Params:
            No params.
        Raises:
            No specific exceptions.
        Returns:
            Nothing returned.
        Extra information:
            Guaranteed to succeed, even if the client is not currently connected.
            After closing, the client can still be reconnected using .connect().
        """
        if self.rcon_socket is not None:
            self.rcon_socket.close()
            self.rcon_socket = None

    def send_packet(self, packet_id, packet_type, packet_body):
        """Sends a packet to the RCON server

        Params:
            packet_id: int; id of packet being sent.
            packet_type: int; type of packet being sent.
            packet_body: str; payload for the packet (usually a command).
        Raises:
            RCONSendError: if any error occurs while sending the data (including a timeout).
        Returns:
            Nothing returned.
        Extra information:
            See RCON protocol specification for what the id and type represent.
        """
        packet = PACKET_PARSER.build([dict(id=packet_id, type=packet_type, body=packet_body)])
        try:
            self.rcon_socket.sendall(packet)
        except socket.timeout as exc:
            raise RCONSendError(CONN_TIMEOUT) from exc
        except Exception as exc:
            raise RCONSendError(SEND_ERROR) from exc

    def receive_packets(self):
        """Receives a variable number of packets from the RCON server

        Params:
            No params.
        Raises:
            InvalidResponse: if the received data could not be parsed into responses.
            RCONReceiveError: if any other error occurs while receiving data (including a timeout).
        Returns:
            list containing the responses received from the server.
        Extra information:
            Each element of the list will be a response with id, type and body.
            These attributes can be accessed with response.id, response.type etc.
        """
        try:
            data = b""
            while True:
                read_data = self.rcon_socket.recv(4096)
                if not read_data:
                    raise RCONClosed(CONN_CLOSED)
                data += read_data
                if len(data) > 2:
                    if data.endswith(b"\x00\x00"):
                        break
            responses = PACKET_PARSER.parse(data)
        except RCONClosed:
            raise
        except socket.timeout as exc:
            raise RCONReceiveError(CONN_TIMEOUT) from exc
        except construct.ConstructError as exc:
            raise InvalidResponse(PARSE_FAILED) from exc
        except Exception as exc:
            raise RCONReceiveError(RECEIVE_ERROR) from exc
        return responses

    def send_command(self, command):
        """Sends a single command to the RCON server

        Params:
            command: str; the command to be executed.
        Raises:
            RCONNotConnected: if the client is not connected to the RCON server.
            ClientBusy: if the client is already busy with another call.
            InvalidResponse: if the server returns an invalid response.
            RCONClosed: if the server closes the connection.
            RCONSendError: if any other error occurs while sending the request (including a timeout).
            RCONReceiveError: if any other error occurs while receiving the response (including a timeout).
        Returns:
            str if data is returned.
            None if no data is returned.
        Extra information:
            Use send_commands if multiple commands are being executed,
            it will be much faster as all of the requests can be sent at once.
            This function cannot be called multiple times simultaneously.
        """
        return self.send_commands(dict(command=command))["command"]

    @handle_socket_errors()
    def send_commands(self, commands):
        """Sends multiple commands to the RCON server

        Params:
            commands: dict; the dict of commands to be executed.
        Raises:
            RCONNotConnected: if the client is not connected to the RCON server.
            ClientBusy: if the client is already busy with another call.
            InvalidResponse: if the server returns an invalid response.
            RCONClosed: if the server closes the connection.
            RCONSendError: if any other error occurs while sending the request (including a timeout).
            RCONReceiveError: if any other error occurs while receiving the response (including a timeout).
        Returns:
            dict of format key: response.
        Extra information:
            Structure of the commands dict:
                key: a name for identifying each command in the response.
                value: command to be executed.
            This function cannot be called multiple times simultaneously.
        """
        self.socket_locked = True
        id_map = {}
        results = {}
        for key, value in commands.items():
            packet_id = self.get_id()
            self.send_packet(packet_id, 2, value)
            id_map[packet_id] = key
        received = 0
        while received < len(commands):
            responses = self.receive_packets()
            for response in responses:
                received += 1
                if response.id not in id_map:
                    raise InvalidResponse(INVALID_ID)
                if not response.body:
                    results[id_map[response.id]] = None
                else:
                    results[id_map[response.id]] = response.body.rstrip()
        self.socket_locked = False
        return results


class AsyncRCONClient(RCONSharedBase):
    """Aysnchronous RCON client for factorio servers

    Params:
        ip_address: str; IP address to connect to.
        port: int; port to connect to.
        password: str; password to use to authenticate.
        **connect_on_init is not supported**
    Raises:
        ImportError: if anyio is not installed.
    Extra information:
        **Async involving this module is performed using anyio**

        anyio allows you to use either asyncio, curio or trio.
        All functions in this class are async.
        If you want to set timeouts, use the cancellation system your existing framework
        provides or use anyio.move_on_after/fail_after.
        See https://anyio.readthedocs.io/en/latest/cancellation.html#timeouts.

        If any exception is raised (all stem from RCONBaseError) during operation,
        it is required that you reconnect to the RCON server (with .connect()).
        The server will not respond to any RCON requests if it is saving, so you should
        use a timeout if you are not prepared to wait a few seconds if the map is
        large or the server slow.
        """
    def __init__(self, ip_address, port, password):
        if not ASYNC_AVAILABLE:
            raise ImportError("anyio must be installed to use the async client", name="anyio")
        super().__init__()
        self.ip_address = ip_address
        self.port = port
        self.password = password


    @async_handle_socket_errors(alive_socket_required=False)
    async def connect(self):
        """Connects to the RCON server asynchronously

        Params:
            No params.
        Raises:
            RCONConnectError: if there is an error connecting to the server.
            InvalidPassword: if the password is incorrect.
            InvalidResponse: if the server returns an invalid response.
        Returns:
            Nothing returned.
        Extra information:
            Use this function to reconnect to the RCON server after an error.
        """
        await self.close()
        self.rcon_failure = False
        try:
            self.rcon_socket = await anyio.connect_tcp(self.ip_address, self.port)
        except Exception as exc:
            raise RCONConnectError(CONNECT_SOCKET_ERROR) from exc
        self.id_seq = 0
        try:
            await self.send_packet(0, 3, self.password)
            responses = await self.receive_packets()
        except RCONBaseError as exc:
            raise RCONConnectError(CONNECT_COMMUNICATION_ERROR) from exc
        for response in responses:
            if response.type == 2:
                if response.id == -1:
                    raise InvalidPassword(INVALID_PASS)
                break
        else:
            raise InvalidResponse(INVALID_ID)

    async def close(self):
        """Closes the connection to the RCON server asynchronously

        Params:
            No params.
        Raises:
            No specific exceptions.
        Returns:
            Nothing returned.
        Extra information:
            Guaranteed to succeed, even if the client is not currently connected.
            After closing, the client can still be reconnected using .connect().
        """
        if self.rcon_socket is not None:
            await self.rcon_socket.aclose()
            self.rcon_socket = None

    async def send_packet(self, packet_id, packet_type, packet_body):
        """Sends a packet to the RCON server asynchronously

        Params:
            packet_id: int; id of packet being sent.
            packet_type: int; type of packet being sent.
            packet_body: str; payload for the packet (usually a command).
        Raises:
            RCONSendError: if any error occurs while sending the data.
        Returns:
            Nothing returned.
        Extra information:
            See RCON protocol specification for what the id and type represent.
        """
        packet = PACKET_PARSER.build([dict(id=packet_id, type=packet_type, body=packet_body)])
        try:
            await self.rcon_socket.execute_script(packet)
        except Exception as exc:
            raise RCONSendError(SEND_ERROR) from exc

    async def receive_packets(self):
        """Receives a variable number of packets from the RCON server asynchronously

        Params:
            No params.
        Raises:
            InvalidResponse: if the received data could not be parsed into responses.
            RCONReceiveError: if any other error occurs while receiving data.
        Returns:
            list containing the responses received from the server.
        Extra information:
            Each element of the list will be a response with id, type and body.
            These attributes can be accessed with response.id, response.type etc.
        """
        try:
            data = b""
            while True:
                try:
                    data += await self.rcon_socket.receive()
                except anyio.EndOfStream as exc:
                    raise RCONClosed(CONN_CLOSED) from exc
                if len(data) > 2:
                    if data.endswith(b"\x00\x00"):
                        break
            responses = PACKET_PARSER.parse(data)
        except RCONClosed:
            raise
        except construct.ConstructError as exc:
            raise InvalidResponse(PARSE_FAILED) from exc
        except Exception as exc:
            raise RCONReceiveError(RECEIVE_ERROR) from exc
        return responses

    async def send_command(self, command):
        """Sends a command to the RCON server asynchronously

        Params:
            command: str; the command to be executed.
        Raises:
            RCONNotConnected: if the client is not connected to the RCON server.
            ClientBusy: if the client is already busy with another call.
            InvalidResponse: if the server returns an invalid response.
            RCONClosed: if the server closes the connection.
            RCONSendError: if any other error occurs while sending the request.
            RCONReceiveError: if any other error occurs while receiving the response.
        Returns:
            str if data is returned.
            None if no data is returned.
        Extra information:
            Use send_commands if multiple commands are being executed at once,
            it will be much faster as all of the requests can be sent an once.
            This function cannot be called multiple times simultaneously, use send_commands.
            This is especially important in an async context.
        """
        return (await self.send_commands(dict(command=command)))["command"]

    @async_handle_socket_errors()
    async def send_commands(self, commands):
        """Sends a dict of commands to the RCON server asynchronously

        Params:
            commands: dict; the dict of commands to be executed.
        Raises:
            RCONNotConnected: if the client is not connected to the RCON server.
            ClientBusy: if the client is already busy with another call.
            InvalidResponse: if the server returns an invalid response.
            RCONClosed: if the server closes the connection.
            RCONSendError: if any other error occurs while sending the request.
            RCONReceiveError: if any other error occurs while receiving the response.
        Returns:
            dict of format key: response.
        Extra information:
            Structure of the commands dict:
                key: a name for identifying each command in the response
                value: command to be executed
            This function cannot be called multiple times simultaneously.
            This is especially important in an async context.
        """
        self.socket_locked = True
        id_map = {}
        results = {}
        for key, value in commands.items():
            packet_id = self.get_id()
            await self.send_packet(packet_id, 2, value)
            id_map[packet_id] = key
        received = 0
        while received < len(commands):
            responses = await self.receive_packets()
            for response in responses:
                received += 1
                if response.id not in id_map:
                    raise InvalidResponse(INVALID_ID)
                if not response.body:
                    results[id_map[response.id]] = None
                else:
                    results[id_map[response.id]] = response.body.rstrip()
        self.socket_locked = False
        return results


CLIENT_BUSY = ("The client is already busy with another call. If sending multiple commands, "
               "use send_commands() rather than calling send_command() multiple times.")
INVALID_PASS = "The RCON password is incorrect"
INVALID_ID = ("The RCON server returned a response with an unknown sequence ID. This means that "
              "a response was received for a command that was not sent. This situation implies "
              "a bug in this RCON library or the RCON server behaving incorrectly. "
              "If this behaviour is intentional, you can use receive_packets().")
PARSE_FAILED = "The RCON server returned data that could not be parsed into response messages"
NOT_CONNECTED = "The RCON client is currently not connected to the server"
RCON_FAILED = ("An error has occured and the client is no longer connected to the RCON server "
               "(reconnect with connect())")
CONN_CLOSED = "The RCON server closed the connection"
CONN_TIMEOUT = "The connection timed out while communicating with the server"
CONNECT_SOCKET_ERROR = "Failed to establish a connection to the server"
CONNECT_COMMUNICATION_ERROR = "Failed to communicate authentication setup to the server"
SEND_ERROR = "Failed to send data to the RCON server"
RECEIVE_ERROR = "Failed to receive data from the RCON server"
