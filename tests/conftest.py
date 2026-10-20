"""Tests must never load real credentials or connect to a trading service."""
import os
import socket
import pytest

os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["TRADING_MODE"] = "PAPER"
os.environ["BINANCE_API_KEY"] = ""
os.environ["BINANCE_API_SECRET"] = ""


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    connect = socket.socket.connect
    connect_ex = socket.socket.connect_ex

    def allowed(address):
        # Windows asyncio implements socketpair using loopback TCP.
        return isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}

    def guarded(sock, address):
        if not allowed(address):
            raise AssertionError("External network disabled in tests")
        return connect(sock, address)

    def guarded_ex(sock, address):
        if not allowed(address):
            raise AssertionError("External network disabled in tests")
        return connect_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_ex)
