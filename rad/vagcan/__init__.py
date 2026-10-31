"""Diagnóstico VAG por CAN (2004 a ~2012): transporte TP2.0 com KWP2000 por dentro.

    tp20.py     canal TP2.0 sobre qualquer interface CAN (send/recv)
    kwp.py      KWP2000 da VAG dentro do canal (mesma interpretação que pela linha K)
    simbus.py   barramento CAN simulado com controladores VAG, para testar sem carro
    elmcan.py   interface CAN através de um adaptador ELM327 / OBDLink (modo de tramas cruas)
"""

SIM_PORT = "VAGCAN:SIMULADOR"


def is_vagcan_sim_port(port):
    return port == SIM_PORT
