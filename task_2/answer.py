import socket
import random

p = 89465071510451101439525273936168511846212445777253520237331698308678503116711043331239104245398349384731391438449504381987949833760932837924368752438143162361048734845462627807539672689912899366514724151681627526140457783428680216876840883532954892702870229862250931999278287416476058989043062146485407855403449
g = 19
y = 30647844200876100331623991677764594348659383358709862404464894077310947688115896216714514674906760959938561827369017433513737387934489781288052406713928150643508607078917491760907503970739687767052853991050484854135323701379976152486903452411422587364742080228378161530191689796166782879086137648697715795619364

HOST = "45.67.32.157"
PORT = 61002

# y^{-1} mod p
inv_y = pow(y, p - 2, p)

# Последовательность запросов, как в коде сервера
challenges = [0, 1, 1, 0, 1]

def main():
    s = socket.socket()
    s.connect((HOST, PORT))

    # Первое приветствие
    data = s.recv(1024)
    print(data.decode(errors="ignore"), end="")

    for i, ch in enumerate(challenges):
        # "Choose C = g^r mod p"
        data = s.recv(1024)
        print(data.decode(errors="ignore"), end="")

        if ch == 0:
            # Раунд, где попросят r
            r = random.randrange(1, p - 1)
            C = pow(g, r, p)
            s.sendall(str(C).encode() + b"\n")

            # "Give me r"
            data = s.recv(1024)
            print(data.decode(errors="ignore"), end="")
            s.sendall(str(r).encode() + b"\n")

        else:
            # Раунд, где попросят x + r (обозначено xr)
            xr = random.randrange(1, p - 1)
            C = (pow(g, xr, p) * inv_y) % p
            s.sendall(str(C).encode() + b"\n")

            # "Give me x+r"
            data = s.recv(1024)
            print(data.decode(errors="ignore"), end="")
            s.sendall(str(xr).encode() + b"\n")

    # Ответ с флагом или ошибкой
    data = s.recv(4096)
    print(data.decode(errors="ignore"))

    s.close()

if __name__ == "__main__":
    main()
