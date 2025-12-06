from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Final, Tuple, List


HOST: Final[str] = "45.67.32.157"
PORT: Final[int] = 61003
BUFFER_SIZE: Final[int] = 4096
ENCODING: Final[str] = "utf-8"


class Field:
    MODULUS: Final[int] = (1 << 255) - 19

    def __init__(self, value: int) -> None:
        self.num: int = value % self.MODULUS

    def __add__(self, other: Field | int) -> Field:
        if isinstance(other, Field):
            return Field(self.num + other.num)
        return Field(self.num + other)

    def __radd__(self, other: int) -> Field:
        return self.__add__(other)

    def __sub__(self, other: Field | int) -> Field:
        if isinstance(other, Field):
            return Field(self.num - other.num)
        return Field(self.num - other)

    def __rsub__(self, other: int) -> Field:
        # other - self
        return Field(other - self.num)

    def __mul__(self, other: Field | int) -> Field:
        if isinstance(other, Field):
            return Field(self.num * other.num)
        return Field(self.num * other)

    def __rmul__(self, other: int) -> Field:
        return self.__mul__(other)

    def __truediv__(self, other: Field | int) -> Field:
        if isinstance(other, Field):
            inv = pow(other.num, self.MODULUS - 2, self.MODULUS)
        else:
            inv = pow(other, self.MODULUS - 2, self.MODULUS)
        return Field(self.num * inv)

    def __pow__(self, exponent: int) -> Field:
        return Field(pow(self.num, exponent, self.MODULUS))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Field):
            return NotImplemented
        return self.num == other.num

    def __repr__(self) -> str:
        return f"Field({self.num})"


Point = Tuple[Field, Field]


@dataclass(frozen=True)
class MontgomeryCurve:
    A: Field

    P_ORDER: Final[int] = (1 << 252) + 27742317777372353535851937790883648493

    def double(self, P: Point) -> Point:
        xP, zP = P
        x2P = (xP + zP) ** 2 * (xP - zP) ** 2
        z2P = xP * Field(4) * zP * ((xP - zP) ** 2 + (self.A + Field(2)) * xP * zP)

        if z2P == Field(0):
            return Field(1), Field(0)

        return x2P, z2P

    def add(self, P: Point, Q: Point, PmQ: Point) -> Point:
        xP, zP = P
        xQ, zQ = Q
        xPmQ, zPmQ = PmQ

        xpq = zPmQ * ((xP - zP) * (xQ + zQ) + (xP + zP) * (xQ - zQ)) ** 2
        zpq = xPmQ * ((xP - zP) * (xQ + zQ) - (xP + zP) * (xQ - zQ)) ** 2

        if zpq == Field(0):
            return Field(1), Field(0)

        return xpq, zpq

    def montgomery_ladder(self, scalar: int, P: Point) -> Point:
        R0: Point = P
        R1: Point = self.double(P)

        for bit in map(int, bin(scalar)[3:]):
            if bit == 0:
                R1 = self.add(R0, R1, P)
                R0 = self.double(R0)
            else:
                R0 = self.add(R0, R1, P)
                R1 = self.double(R1)

        return R0

    @staticmethod
    def point_from_token(token: int) -> Point:
        x = Field(token)
        return x, Field(1)

    @staticmethod
    def token_from_point(P: Point) -> int:
        x, z = P
        return int((x / z).num)


class VotingServerClient:
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
        self._socket: socket.socket | None = None

    def __enter__(self) -> VotingServerClient:
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

    def recv(self, max_bytes: int = 1024) -> str:
        sock = self._ensure_socket()
        data = sock.recv(max_bytes)
        return data.decode(self._encoding, errors="ignore")

    def send_line(self, text: str) -> None:
        sock = self._ensure_socket()
        payload = f"{text}\n".encode(self._encoding)
        sock.sendall(payload)


@dataclass
class VotingContext:
    user_id: int
    user_token: int
    base_point_Q: Point


class VotingAttack:
    def __init__(self, client: VotingServerClient, curve: MontgomeryCurve) -> None:
        self._client = client
        self._curve = curve

    def execute(self) -> None:
        greeting = self._client.recv()
        print(greeting, end="")

        context = self._init_context()

        print("Recovered Q")

        tokens = self._generate_tokens_for_ids(context.base_point_Q, start_id=1, end_id=10)
        for user_id, token in tokens:
            print(f"ID {user_id}: token {hex(token)}")

        self._cast_votes(tokens)
        self._print_flag()

    def _init_context(self) -> VotingContext:
        self._client.recv()
        self._client.send_line("1")
        id_line = self._client.recv()
        user_id = int(id_line.split(": ")[1].strip())
        print(f"My ID: {user_id}")

        self._client.recv()
        self._client.send_line("2")
        token_line = self._client.recv()
        user_token = int(token_line.split(": ")[1].strip(), 16)
        print(f"My token: {hex(user_token)}")

        T = self._curve.point_from_token(user_token)
        inv_id = pow(user_id, -1, self._curve.P_ORDER)
        Q = self._curve.montgomery_ladder(inv_id, T)

        return VotingContext(
            user_id=user_id,
            user_token=user_token,
            base_point_Q=Q,
        )

    def _generate_tokens_for_ids(self, Q: Point, start_id: int, end_id: int) -> List[tuple[int, int]]:
        tokens: List[tuple[int, int]] = []

        for user_id in range(start_id, end_id + 1):
            T_id = self._curve.montgomery_ladder(user_id, Q)
            token = self._curve.token_from_point(T_id)
            tokens.append((user_id, token))

        return tokens

    def _cast_votes(self, tokens: List[tuple[int, int]]) -> None:
        for user_id, token in tokens:
            self._client.recv()
            self._client.send_line("3")

            self._client.recv()
            self._client.send_line(str(user_id))

            self._client.recv()
            self._client.send_line(f"{token:x}")

            result = self._client.recv()
            print(f"Vote {user_id}: {result.strip()}")

    def _print_flag(self) -> None:
        self._client.recv()
        self._client.send_line("4")
        flag_result = self._client.recv(BUFFER_SIZE)
        print("Final result:", flag_result.strip())


def main() -> None:
    curve = MontgomeryCurve(A=Field(486662))

    with VotingServerClient(HOST, PORT) as client:
        attack = VotingAttack(client, curve)
        attack.execute()


if __name__ == "__main__":
    main()
