import socket
import random
import math

HOST = "45.67.32.157"
PORT = 61001

def int_to_str(n: int) -> str:
    # та же логика, что у сервера
    return bytes.fromhex(hex(n)[2:]).decode()

def main():
    s = socket.socket()
    s.connect((HOST, PORT))

    # накапливаем всё, что пришло, пока не увидим приглашение ввести шифртекст
    buf = ""
    while "Ciphertext to decrypt:" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk.decode(errors="ignore")

    print(buf)  # просто чтобы видеть, что сервер прислал

    # парсим e, N, enc_flag
    e = N = enc_flag = None
    for line in buf.splitlines():
        line = line.strip()
        if line.startswith("e ="):
            e = int(line.split("=", 1)[1].strip())
        elif line.startswith("N ="):
            N = int(line.split("=", 1)[1].strip())
        elif line.startswith("Encrypted flag:"):
            enc_flag = int(line.split(":", 1)[1].strip())

    assert e is not None and N is not None and enc_flag is not None, "Не удалось распарсить e, N, enc_flag"

    # выбираем случайный множитель s, взаимно простой с N
    while True:
        s_mul = random.randrange(2, N - 1)
        if math.gcd(s_mul, N) == 1:
            break

    # C' = enc_flag * s^e mod N
    C_prime = (enc_flag * pow(s_mul, e, N)) % N

    print("[*] Отправляю модифицированный шифртекст...")
    s.sendall(str(C_prime).encode() + b"\n")

    # читаем ответ оракула (одного recv обычно хватает, но можно и в цикле)
    resp = s.recv(4096).decode(errors="ignore")
    print(resp)

    # парсим "Decrypted message: <число>"
    dec_value = None
    for line in resp.splitlines():
        line = line.strip()
        if line.startswith("Decrypted message:"):
            dec_value = int(line.split(":", 1)[1].strip())
            break

    assert dec_value is not None, "Не удалось распарсить ответ оракула"

    # dec_value = M * s (mod N) → M = dec_value * s^{-1} mod N
    s_inv = pow(s_mul, -1, N)   # Python 3.8+
    m_int = (dec_value * s_inv) % N
    length = (m_int.bit_length() + 7) // 8
    flag = m_int.to_bytes(length, byteorder="big")

    print(flag.decode())

    s.close()

if __name__ == "__main__":
    main()
