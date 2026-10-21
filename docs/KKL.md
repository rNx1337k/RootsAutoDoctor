# Cabo KKL 409.1 (FTDI) no Roots Auto Doctor

Via de diagnóstico independente, sem software proprietário: um cabo **KKL 409.1** com chip **FTDI**
(ou CH340) aparece como porta COM normal e o Roots Auto Doctor fala diretamente com a linha K
(KW1281 e KWP2000). É o caminho recomendado para validar leituras reais em VAG até ~2005.

## O que já está implementado (auditado a 2026-10-21)

Auditoria do percurso completo no código, não pelo README:

| Etapa | Onde | Estado |
|---|---|---|
| Deteção de portas COM + chip (FTDI/CH340) e Latency Timer | `rad/cable.py`, `rad/kline.py:list_serial_ports` | Implementado |
| Abrir/fechar a porta série, baud, BREAK, DTR/RTS, timeouts | `rad/kline.py` (pyserial) | Implementado |
| Init a 5 baud (temporização absoluta por BREAK), deteção de eco, procura de DTR/RTS | `rad/kline.py:_five_baud_init`, `find_lines` | Implementado |
| Erros de porta → mensagem concreta (não "Erro de ligação" genérico) | `rad/kline.py` → `KLineError`/`InterfaceError` | Implementado |
| Estados de ligação (sem interface / inacessível / aberta sem centralina / ligado / erro) | `rad/connstate.py` + `rad/worker.py` | Implementado |
| KW1281: identificação, avarias, grupos, ajuste básico, adaptação, login, codificação, teste de saídas | `rad/protocols/kw1281.py` | Implementado |
| KWP2000 (linha K e J2534): identificação, avarias, grupos | `rad/protocols/kwp2000.py` | Implementado (leitura) |
| KWP2000 escrita (adaptação, codificação, login, saídas) | `rad/protocols/kwp2000.py` | **Não implementado** (`NotSupported`) — por desenho |
| Comunicação fora da UI (thread), keep-alive, desconexões, fecho forçado | `rad/worker.py` | Implementado |

**Conclusão da auditoria:** o suporte KKL está completo ao nível do código e testado contra o simulador e
contra uma **resposta real de centralina** (ver abaixo). Falta só a validação física num carro com o cabo KKL
— que precisa do hardware.

## Prova com dados reais (sem carro)

`tests/test_capture_replay.py` usa a resposta KW1281 em claro de um **Audi A3 8L 1.9 TDI** ("EDC SG 1536"),
gravada por USBPcap a 21/10/2026. O VCDS mostrou no mesmo instante 5 avarias; o `read_faults()` do Roots Auto
Doctor, sobre os mesmos bytes, devolve exatamente as mesmas:

| Bytes da centralina | Roots Auto Doctor | VCDS (fotografia) |
|---|---|---|
| `44 90 A3` | 17552 · 35 · intermitente | 17552 P1144 35-10 |
| `46 8E A3` | 18062 · 35 · intermitente | 18062 P1654 35-10 |
| `46 7B A3` | 18043 · 35 · intermitente | 18043 P1635 35-10 |
| `46 7C 23` | 18044 · 35 · estático | 18044 P1636 35-00 |
| `46 7D A3` | 18045 · 35 · intermitente | 18045 P1637 35-10 |

Estes bytes são a resposta da própria centralina (bloco KW1281 0xFC), igual à que um cabo KKL entrega. Não
têm nada do protocolo proprietário do cabo HEX. A origem é sempre identificada como **simulação** quando
repetida pelo emulador — nunca apresentada como leitura ao vivo.

## Validação no carro (quando tiveres o cabo KKL)

1. Liga o cabo à porta USB. Em **Opções → Detectar cabo**, confirma que aparece como porta COM (FTDI/CH340).
   Para FTDI, põe o Latency Timer a 1 ms (Gestor de Dispositivos → Portas (COM) → Propriedades → Avançadas).
2. Em **Opções**, escolhe essa porta e liga **Registo detalhado** (guarda todos os bytes para o pacote de suporte).
3. Cabo na ficha OBD, **ignição ligada, motor desligado**.
4. **Opções → Diagnóstico da ligação** com o endereço `01`:
   - Deves ver: cabo na COM → porta aberta → **eco da linha K OK** → ligação ao 01 → identificação.
   - Sem eco com a ignição ligada: experimenta Velocidade = 9600 / 10400 em Opções; confirma a ficha OBD.
5. **01-Motor → ler avarias.** Neste carro de referência, devem aparecer as 5 avarias da tabela acima.
   Compara com a fotografia do VCDS: têm de ser os mesmos códigos e o mesmo estado (35-10 / 35-00).
6. Lê a identificação (deve conter "EDC" e "1536") e o grupo de medição 001.
7. No fim: **Opções → Pacote de suporte** e guarda o zip. Envia-o com o resultado de cada passo.

Nesta fase, só leitura: não apagues avarias nem uses codificação/adaptação até a leitura estar confirmada.

## O que falta validar com hardware

- Eco da linha K, init a 5 baud e KW1281/KWP2000 com uma centralina real através do cabo KKL (até aqui, só
  simulador e a resposta gravada acima).
- Fórmulas de medição raras (`rad/vag_data.py`) e o byte de estado das avarias em KWP2000 (a tabela é a do
  KW1281; confirmar num carro KWP2000 com avarias conhecidas).

## Próxima tarefa recomendada

Obter um cabo KKL 409.1 com FTDI e correr a secção "Validação no carro" neste Audi A3 8L. Com as 5 avarias
confirmadas pelo programa, a leitura de diagnóstico fica provada com hardware real — o passo que falta para a
Fase 1 fechar e para o programa poder ser apresentado a oficinas.
