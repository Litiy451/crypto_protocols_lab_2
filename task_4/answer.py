from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Final, Optional


HOST: Final[str] = "45.67.32.157"
PORT: Final[int] = 61004
BUFFER_SIZE: Final[int] = 4096
ENCODING: Final[str] = "utf-8"


@dataclass(frozen=True)
class PowTask:
    a: int
    q: int
    y: int


class PowTaskParser:
    @staticmethod
    def parse(chunk: str) -> PowTask:
        lines = chunk.strip().splitlines()
        if not lines:
            raise ValueError("Пустой chunk для парсинга PowTask")

        line = lines[0]

        try:
            _, rest = line.split("pow(x,", 1)
            args, rhs = rest.split(")=", 1)
        except ValueError as exc:
            raise ValueError(f"Некорректный формат строки задачи: {line!r}") from exc

        a_str, q_str = args.split(",", 1)
        a = int(a_str)
        q = int(q_str)
        y = int(rhs)

        return PowTask(a=a, q=q, y=y)


class SubgroupOrderFinder:
    def __init__(self, small_factor_limit: int = 1_000_000) -> None:
        self._limit = small_factor_limit

    def find_large_prime_factor(self, q: int) -> int:
        n = q - 1
        d = 2

        while d <= self._limit and d * d <= n:
            while n % d == 0:
                n //= d
            d += 1

        return n


class ChallengeServerClient:
    def __init__(
        self,
        host: str = HOST,
        port: int = PORT,
        buffer_size: int = BUFFER_SIZE,
        encoding: str = ENCODING,
    ) -> None:
        self._host = host
        self._port = port
        self._buffer_size = buffer_size
        self._encoding = encoding
        self._socket: Optional[socket.socket] = None

    def __enter__(self) -> ChallengeServerClient:
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

    def recv(self, max_bytes: int | None = None) -> str:
        sock = self._ensure_socket()
        size = max_bytes or self._buffer_size
        data = sock.recv(size)
        return data.decode(self._encoding, errors="ignore")

    def send_line(self, text: str) -> None:
        sock = self._ensure_socket()
        payload = f"{text}\n".encode(self._encoding)
        sock.sendall(payload)


class DiscreteLogSolver:
    def __init__(
        self,
        client: ChallengeServerClient,
        parser: PowTaskParser,
        order_finder: SubgroupOrderFinder,
    ) -> None:
        self._client = client
        self._parser = parser
        self._order_finder = order_finder

        self._p: Optional[int] = None
        self._q: Optional[int] = None

    def run(self) -> None:
        greeting = self._client.recv(BUFFER_SIZE)
        print(greeting, end="")

        while True:
            chunk = self._client.recv(BUFFER_SIZE)
            if not chunk:
                break

            print(chunk, end="")

            if "pow(x," not in chunk:
                if any(marker in chunk for marker in ("Here is flag", "You failed", "Error:")):
                    break
                continue

            task = self._parser.parse(chunk)
            self._ensure_group_parameters(task.q)

            assert self._p is not None
            assert self._q is not None

            inv_a = pow(task.a, -1, self._p)

            x = pow(task.y, inv_a, self._q)

            self._client.send_line(str(x))

    def _ensure_group_parameters(self, q: int) -> None:
        if self._p is None:
            self._p = self._order_finder.find_large_prime_factor(q)
            self._q = q
        else:
            if self._q != q:
                raise ValueError(f"Ожидали неизменный модуль q={self._q}, а получили q={q}")


def main() -> None:
    parser = PowTaskParser()
    order_finder = SubgroupOrderFinder()

    with ChallengeServerClient(HOST, PORT) as client:
        solver = DiscreteLogSolver(client, parser, order_finder)
        solver.run()


if __name__ == "__main__":
    main()
