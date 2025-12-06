from __future__ import annotations

import math
import random
import socket
from dataclasses import dataclass
from typing import Final


HOST: Final[str] = "45.67.32.157"
PORT: Final[int] = 61001
BUFFER_SIZE: Final[int] = 4096
ENCODING: Final[str] = "utf-8"


@dataclass
class RsaChallenge:
    e: int
    n: int
    encrypted_flag: int


class RsaOracleClient:
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

    def __enter__(self) -> RsaOracleClient:
        self._socket = socket.create_connection((self._host, self._port))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    @property
    def encoding(self) -> str:
        return self._encoding

    @property
    def buffer_size(self) -> int:
        return self._buffer_size

    def _ensure_socket(self) -> socket.socket:
        if self._socket is None:
            raise RuntimeError("Соединение с сервером ещё не установлено")
        return self._socket

    def receive_until(self, prompt: str) -> str:
        sock = self._ensure_socket()
        parts: list[str] = []

        while True:
            chunk = sock.recv(self._buffer_size)
            if not chunk:
                break

            decoded = chunk.decode(self._encoding, errors="ignore")
            parts.append(decoded)

            if prompt in decoded:
                break

        return "".join(parts)

    def send_line(self, text: str) -> None:
        sock = self._ensure_socket()
        payload = f"{text}\n".encode(self._encoding)
        sock.sendall(payload)

    def receive_once(self) -> str:
        sock = self._ensure_socket()
        data = sock.recv(self._buffer_size)
        return data.decode(self._encoding, errors="ignore")


class RsaPaddingOracleAttacker:
    def __init__(self, client: RsaOracleClient) -> None:
        self._client = client

    def execute(self) -> str:
        banner = self._client.receive_until("Ciphertext to decrypt:")
        print(banner)

        challenge = self._parse_challenge(banner)

        s_mul = self._choose_random_coprime(challenge.n)

        c_prime = (challenge.encrypted_flag * pow(s_mul, challenge.e, challenge.n)) % challenge.n

        print("[*] Отправляю модифицированный шифртекст...")
        self._client.send_line(str(c_prime))

        response = self._client.receive_once()
        print(response)

        dec_value = self._parse_decrypted_message(response)

        plaintext_bytes = self._recover_plaintext(challenge, dec_value, s_mul)

        return plaintext_bytes.decode(self._client.encoding, errors="replace")

    @staticmethod
    def _parse_challenge(raw_text: str) -> RsaChallenge:
        e: int | None = None
        n: int | None = None
        enc_flag: int | None = None

        for line in raw_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("e ="):
                e = int(stripped.split("=", 1)[1].strip())
            elif stripped.startswith("N ="):
                n = int(stripped.split("=", 1)[1].strip())
            elif stripped.startswith("Encrypted flag:"):
                enc_flag = int(stripped.split(":", 1)[1].strip())

        if e is None or n is None or enc_flag is None:
            raise ValueError("Не удалось распарсить e, N или encrypted_flag из ответа сервера")

        return RsaChallenge(e=e, n=n, encrypted_flag=enc_flag)

    @staticmethod
    def _choose_random_coprime(modulus: int) -> int:
        if modulus <= 3:
            raise ValueError("Слишком маленький модуль N")

        while True:
            candidate = random.randrange(2, modulus - 1)
            if math.gcd(candidate, modulus) == 1:
                return candidate

    @staticmethod
    def _parse_decrypted_message(response: str) -> int:
        for line in response.splitlines():
            stripped = line.strip()
            if stripped.startswith("Decrypted message:"):
                return int(stripped.split(":", 1)[1].strip())

        raise ValueError("Не удалось найти строку 'Decrypted message:' в ответе сервера")

    @staticmethod
    def _recover_plaintext(
        challenge: RsaChallenge,
        oracle_decrypted_value: int,
        multiplier: int,
    ) -> bytes:
        s_inv = pow(multiplier, -1, challenge.n)
        m_int = (oracle_decrypted_value * s_inv) % challenge.n

        length = (m_int.bit_length() + 7) // 8
        return m_int.to_bytes(length, byteorder="big")


def main() -> None:
    with RsaOracleClient(HOST, PORT) as client:
        attacker = RsaPaddingOracleAttacker(client)
        flag = attacker.execute()
        print(flag)


if __name__ == "__main__":
    main()
