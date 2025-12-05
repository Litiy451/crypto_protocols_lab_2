import socket

HOST = "45.67.32.157"
PORT = 61004

def parse_task(chunk: str):
    """
    Пример строки:
    "1/100: pow(x,1234,987654321...)=5678\nx="
    Нужно достать a, q, y.
    """
    lines = chunk.strip().splitlines()
    line = lines[0]  # "1/100: pow(x,a,q)=y"

    # отделяем часть после "pow(x,"
    _, rest = line.split("pow(x,", 1)      # rest: "a,q)=y"
    args, rhs = rest.split(")=", 1)        # args: "a,q" ; rhs: "y"

    a_str, q_str = args.split(",", 1)

    a = int(a_str)
    q = int(q_str)
    y = int(rhs)

    return a, q, y

def find_real_p_from_q(q: int, limit: int = 1_000_000) -> int:
    """
    Ищем большой простой множитель p из разложения q-1 = f * p,
    выдирая все маленькие простые множители из q-1.
    """
    n = q - 1
    d = 2
    # пробегаем маленькие делители и полностью выкусываем их из n
    while d <= limit and d * d <= n:
        while n % d == 0:
            n //= d
        d += 1
    # теперь n должен быть тем самым большим простым p
    return n

def main():
    s = socket.socket()
    s.connect((HOST, PORT))

    # приветствие
    data = s.recv(4096)
    print(data.decode(errors="ignore"), end="")

    p = None
    q = None

    while True:
        data = s.recv(4096)
        if not data:
            break
        text = data.decode(errors="ignore")
        print(text, end="")

        if "pow(x," not in text:
            # пока нет задачи — продолжаем читать
            if "Here is flag" in text or "You failed" in text or "Error:" in text:
                break
            continue

        # парсим текущую задачу
        a, q_task, y = parse_task(text)

        if p is None:
            # один раз вычисляем настоящий порядок подгруппы p
            p = find_real_p_from_q(q_task)
            q = q_task
            # можно для отладки вывести:
            # print("\n[DEBUG] p bit_length:", p.bit_length())

        else:
            # убеждаемся, что модуль не меняется
            assert q == q_task

        # инвертируем a по модулю p
        inv_a = pow(a, -1, p)  # здесь уже не должно падать

        # x = y^{a^{-1} mod p} mod q
        x = pow(y, inv_a, q)

        s.sendall(str(x).encode() + b"\n")

    s.close()

if __name__ == "__main__":
    main()
