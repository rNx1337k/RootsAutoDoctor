"""Diagnóstico normalizado multimarca: OBD-II/EOBD (SAE J1979 / ISO 15031), ISO-TP (ISO 15765-2) e UDS
(ISO 14229), independente da interface.

Camadas (cada uma só conhece a de baixo):

  interface física   rad/obd/elm327.py   adaptador ELM327 (porta série, comandos AT documentados)
                     rad/obd/isotp.py    ISO-TP sobre um barramento CAN "cru" (CanBus)
  ligação            "link": objecto com  request(payload, target=None) -> [Response]
  serviços           rad/obd/j1979.py    modos OBD-II 01/02/03/04/07/09/0A
                     rad/obd/uds.py      UDS só de leitura (+ apagar avarias com confirmação)
  sessão             rad/obd/session.py  ciclo de vida, estados e resultados para a interface gráfica

Nada aqui depende do Qt, para poder ser testado sem janela e sem hardware.
"""
