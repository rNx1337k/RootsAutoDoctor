# Roots Auto Doctor

Programa de diagnóstico automóvel ao estilo VCDS, começando pelo grupo VAG em linha K
(TDI e restantes modelos até ~2005). Fala directamente com as centralinas pelos mesmos
protocolos que o VCDS usa nestes carros:

- **KW1281** (o "KWP1281" do VCDS) — init a 5 baud, auto-detecção 10400 / 9600 / 4800 baud
- **KWP2000 sobre linha K** (ISO 14230) — init a 5 baud, como nos EDC15/EDC16 e ABS Mk60

## Novidades da v0.2

- Logo próprio (mostrador + pulso + raízes em pistas de circuito) e ícone da aplicação
- Tema inspirado no painel de instrumentos VAG: azul-noite, escala azul, ponteiros vermelhos
- Ecrã de arranque, barra lateral com indicador de pulso (bate enquanto há ligação)
- Valores de medição em mostradores com ponteiro e histórico das últimas leituras
- Auto-Scan em mosaicos coloridos (verde sem avarias, âmbar com avarias, vermelho sem comunicação);
  clique num mosaico para abrir o controlador
- **Relatório para o cliente** em PDF ou página web: logo, dados da oficina (Opções),
  dados do veículo (Início), avarias por controlador e observações
- Notificações discretas em vez de janelas para confirmações

Para regenerar o logo: `python tools/make_logo.py` (precisa de Pillow).

## Instalar e correr (Windows)

1. Instalar Python 3.10+ (marcar "Add Python to PATH").
2. Duplo clique em `run.bat` — na primeira vez cria o ambiente e instala PySide6 + pyserial.
3. Para gerar um `.exe`: `build_exe.bat`.

Manualmente: `pip install -r requirements.txt` e `python main.py`.

## Cabo

Funciona com cabos **KKL "VAG-COM 409.1"** e clones VCDS de **linha K com chip FTDI ou CH340**
— os que aparecem no Gestor de Dispositivos como porta COM.

- Em cabos FTDI: Propriedades da porta COM → Definições → Avançadas → **Latency Timer = 1 ms**.
  Sem isto funciona, mas a leitura dos grupos fica bastante mais lenta.
- Cabos **HEX-USB+CAN / HEX-V2** (originais ou clones) têm firmware fechado da Ross-Tech:
  não aparecem como porta COM e só funcionam com o VCDS.

## Primeiro teste

1. Opções → escolher a porta → **Testar interface** (com o cabo na ficha OBD e ignição ligada
   deve dizer "eco da linha K OK").
2. Controladores → **01 Electrónica do motor**.
3. Separadores: Informação, Avarias, Valores de medição (3 grupos em simultâneo + gravação CSV),
   Ajustes básicos, Adaptação, Codificação, Login, Testes de saídas.
4. **Auto-Scan** varre todos os módulos comuns e gera relatório (copiar / guardar .txt).

Sem carro: Início → **Modo simulador** (endereços 01 motor, 03 ABS em KWP2000, 17 painel a 9600 baud).

## Funções por protocolo

| Função | KW1281 | KWP2000 (linha K) |
|---|---|---|
| Identificação (peça, componente) | ✔ | ✔ |
| Codificação / WSC (leitura) | ✔ | — |
| Ler / apagar avarias | ✔ | ✔ |
| Valores de medição (grupos) | ✔ | ✔ |
| Ajustes básicos | ✔ | próxima versão |
| Adaptação (ler / testar / gravar) | ✔ | próxima versão |
| Codificar | ✔ | próxima versão |
| Login | ✔ | próxima versão |
| Testes de saídas | ✔ | próxima versão |

## Estrutura

```
main.py                    arranque da aplicação
rad/kline.py               porta série, eco, init 5 baud por bit-banging (BREAK)
rad/protocols/kw1281.py    protocolo KW1281 (blocos com complemento byte a byte)
rad/protocols/kwp2000.py   KWP2000 sobre linha K
rad/session.py             init + detecção de protocolo + API única
rad/vag_data.py            módulos, códigos de avaria, tipos de avaria, fórmulas de medição
rad/simulator.py           centralinas simuladas ao nível do byte
rad/worker.py              thread de comunicação (keep-alive, leitura contínua, auto-scan)
rad/ui/                    interface PySide6
tests/test_simulator.py    testes de ponta a ponta contra o simulador
```

## Se algo falhar no carro

Active **Opções → Registar bytes em bruto** e envie o conteúdo do "Registo de comunicação":
mostra exactamente o que o carro respondeu e permite corrigir rapidamente.

## Próximos passos

- Ajustes básicos, adaptação e codificação em KWP2000 (EDC16, painéis UDS-on-K)
- Base de dados de avarias e de nomes de grupos de medição mais completa
- Carros com CAN (VAG pós-2005 e outras marcas): exige outra interface (ELM327/OBDLink ou J2534)
