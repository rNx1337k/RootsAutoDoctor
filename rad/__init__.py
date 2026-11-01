APP_NAME = "Roots Auto Doctor"
VERSION = "1.14.2"


def technician_mode(argv=None, environ=None):
    """Modo técnico (só desenvolvimento e suporte): mostra o registo de comunicação e as opções avançadas da
    interface (velocidade, eco, protocolo, modo do cabo, simulador J2534). Liga-se com o argumento --tecnico ou
    com a variável RAD_TECNICO=1. O cliente nunca o vê: a interface normal usa só linguagem de oficina."""
    import os
    import sys
    argv = sys.argv if argv is None else argv
    environ = os.environ if environ is None else environ
    return "--tecnico" in argv or environ.get("RAD_TECNICO") == "1"
