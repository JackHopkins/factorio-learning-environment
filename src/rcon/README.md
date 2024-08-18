# factorio-rcon-py

A simple factorio RCON client

## Install

`pip3 install factorio-rcon-py`

## Usage

Example:
```python
import factorio_rcon

client = factorio_rcon.RCONClient("127.0.0.1", 12345, "mypassword")
response = client.send_command("/help")
```

All documentation is in the docstrings of each function/class. Currently,
there is no docs website or similar but one is planned.

Asynchronous usage of this module is possible thanks to [anyio](https://github.com/agronholm/anyio). This means that you can use the async client with asyncio, curio and trio. Use the AsyncRCONClient class. More details are in its docstring.

Available functions in both classes are (see docstrings for more info):
* connect - Connects to the RCON server.
* close - Closes the connection to the RCON server.
* send_packet - Sends a packet to the RCON server.
* receive_packets - Receives a variable number of packets from the RCON server.
* send_command - Sends a single command to the RCON server.
* send_commands - Sends multiple commands to the RCON server.

The functions for sending/receiving packets are available in case you want to
write your own packet handlers, but in most cases you will never need to touch
these and can use send_command(s).

## Mentions

Thanks to [Truman Kilen](https://github.com/trumank) for the initial code / idea.

## License

GPLV3
