from __future__ import annotations

import random
import socket
from dataclasses import dataclass
from typing import Final


P: Final[int] = (
    89465071510451101439525273936168511846212445777253520237331698308678503116711043331239104245398349384731391438449504381987949833760932837924368752438143162361048734845462627807539672689912899366514724151681627526140457783428680216876840883532954892702870229862250931999278287416476058989043062146485407855403449
)
G: Final[int] = 19
Y: Final[int] = (
    30647844200876100331623991677764594348659383358709862404464894077310947688115896216714514674906760959938561827369017433513737387934489781288052406713928150643508607078917491760907503970739687767052853991050484854135323701379976152486903452411422587364742080228378161530191689796166782879086137648697715795619364
)

HOST: Final[str] = "45.67.32.157"
PORT: Final[int] = 61002
BUFFER_SIZE: Final[int] = 4096
ENCODING: Final[str] = "utf-8"

DEFAULT_CHALLENGES: Final[list[int]] = [0, 1, 1, 0, 1]


class DiffieHellmanProofClient:
    def __init__(
        self,
        host: str = HOST,
        port: int = PORT,
        buffer_size: int = BUFFER_SIZE,
        encoding: str = ENCODING,
    ) -> None:
        self._host: str = host
        self._port: int = port
        self._buffer_size: int = buffer_size
        self._encoding: str = encoding
        self._socket: socket.socket | None = None

    def __enter__(self) -> DiffieHellmanProofClient:
        self._socket = socket.create_connection((self._host, self._port))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def _ensure_socket(self) -> socket.socket:
        if self._socket is None:
            raise RuntimeError("Соединение с сервером не установлено")
        return self._socket

    @property
    def encoding(self) -> str:
        return self._encoding

    def receive(self, max_bytes: int | None = None) -> str:
        sock = self._ensure_socket()
        chunk_size = max_bytes or self._buffer_size
        data = sock.recv(chunk_size)
        return data.decode(self._encoding, errors="ignore")

    def send_line(self, text: str) -> None:
        sock = self._ensure_socket()
        payload = f"{text}\n".encode(self._encoding)
        sock.sendall(payload)


@dataclass
class DiscreteLogParameters:
    p: int
    g: int
    y: int

    @property
    def inv_y(self) -> int:
        return pow(self.y, self.p - 2, self.p)


class DiscreteLogProver:
    def __init__(
        self,
        client: DiffieHellmanProofClient,
        params: DiscreteLogParameters,
        challenges: list[int] | None = None,
    ) -> None:
        self._client = client
        self._params = params
        self._challenges: list[int] = challenges if challenges is not None else list(DEFAULT_CHALLENGES)

    def run_protocol(self) -> None:
        greeting = self._client.receive(1024)
        print(greeting, end="")

        for round_index, ch in enumerate(self._challenges):
            self._run_round(round_index, ch)

        final_response = self._client.receive(BUFFER_SIZE)
        print(final_response, end="")

    def _run_round(self, index: int, challenge_type: int) -> None:
        prompt = self._client.receive(1024)
        print(prompt, end="")

        if challenge_type == 0:
            self._handle_r_round()
        else:
            self._handle_x_plus_r_round()

    def _handle_r_round(self) -> None:
        r = random.randrange(1, self._params.p - 1)
        c_value = pow(self._params.g, r, self._params.p)

        self._client.send_line(str(c_value))

        prompt = self._client.receive(1024)
        print(prompt, end="")

        self._client.send_line(str(r))

    def _handle_x_plus_r_round(self) -> None:
        xr = random.randrange(1, self._params.p - 1)

        c_value = (pow(self._params.g, xr, self._params.p) * self._params.inv_y) % self._params.p

        self._client.send_line(str(c_value))

        prompt = self._client.receive(1024)
        print(prompt, end="")

        self._client.send_line(str(xr))


def main() -> None:
    params = DiscreteLogParameters(p=P, g=G, y=Y)

    with DiffieHellmanProofClient(HOST, PORT) as client:
        prover = DiscreteLogProver(client=client, params=params)
        prover.run_protocol()


if __name__ == "__main__":
    main()
