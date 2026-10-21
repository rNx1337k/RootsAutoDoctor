# Auditoria técnica — Roots Auto Doctor

**Data:** 21/10/2026 · **Base auditada:** `main` @ `4baa7e7` (v1.2.0), igual à cópia local em
`Desktop\RootsAutoDoctor` (código-fonte idêntico; a cópia local tem a mais apenas scripts e resultados de testes
com o cabo HEX).

As referências de linha são as da versão auditada (antes das correcções). Gravidade: **CRÍTICO** (pode causar
danos ou operações indevidas), **ALTO** (falha funcional importante ou informação enganosa), **MÉDIO**
(fiabilidade, usabilidade), **BAIXO** (manutenção).

## 1. Inventário

| Área | Ficheiros | Linhas |
|---|---|---|
| Arranque | `main.py` | 114 |
| Camada física | `rad/kline.py`, `rad/ftdi_direct.py`, `rad/d2xx.py`, `rad/d2xx_bridge.py`, `rad/hexmcu.py`, `rad/j2534.py`, `rad/j2534_bridge.py`, `rad/cable.py` | ~2 180 |
| Protocolos | `rad/protocols/kw1281.py`, `rad/protocols/kwp2000.py`, `rad/session.py` | ~660 |
| Thread de comunicação | `rad/worker.py` | 513 |
| Dados VAG / assistente | `rad/vag_data.py`, `rad/fault_advice.py`, `rad/guided.py`, `rad/ui_score.py` | ~990 |
| Histórico / relatórios / registos | `rad/history.py`, `rad/report.py`, `rad/applog.py`, `rad/settings.py`, `rad/selftest.py` | ~530 |
| Simulador | `rad/simulator.py` | 356 |
| Interface | `rad/ui/` (janela, 7 páginas, widgets, estilo, paleta) | ~4 200 |
| Testes | `tests/` (15 ficheiros, 88 testes) | ~2 100 |
| Ferramentas / build | `tools/`, `*.bat`, `installer/RootsAutoDoctor.iss` | — |

Pontos de entrada: `main.py` (janela; `--selftest` para o auto-teste), `tools/hex_probe.py`, `tools/hex_capture.py`,
`tools/get_runtime.py`. Fluxo: UI → `Worker.submit()` → `QThread` → `ECUSession` → `KW1281`/`KWP2000` →
`KLine` (pyserial / D2XX / FTDI directo / simulador) ou `J2534Link` (ponte em processo separado) → sinais Qt → UI.

**Estado inicial dos testes**
- No PC do utilizador (`resultado_testes2.txt`, versão ligeiramente anterior): 80/80.
- Neste ambiente de auditoria (Linux, sem acesso ao PyPI, portanto sem PySide6): 73 OK / 10 falhas, todas
  ambientais (falta de PySide6; o auto-teste precisa do `runtime/py32` do Windows). Com um stub mínimo de
  `QtCore` fora do projecto (só para correr a lógica do Worker): 84 OK / 4 falhas (3 testes de UI que precisam do
  `QtWidgets` + o auto-teste do runtime Windows).

## 2. O que está bem (preservado)

- Camada K-line sólida: init a 5 baud por BREAK com temporização absoluta (`kline.py:214-287`), detecção de eco,
  cancelamento do init, procura de DTR/RTS e memória por porta.
- O clone HEX-USB+CAN foi tratado com rigor: só se envia a mudança de modo depois de uma resposta válida com
  checksum (`hexmcu.py:180-196`); o programa diz claramente que a leitura de centralinas por esse cabo ainda não
  existe. **O HEX-V2 / HEX-USB+CAN não é apresentado como funcional** — correcto, e mantém-se assim.
- Pontes D2XX/J2534 em processo separado (32/64 bits), com simuladores para testes sem hardware.
- `compare()` do histórico já só compara módulos lidos nas duas visitas (`history.py:195-207`).
- Testes de robustez com injecção de falhas e fuzzing dos parsers.

## 3. Problemas encontrados

### ALTO

| # | Ficheiro:linhas | Problema | Estado |
|---|---|---|---|
| A1 | `protocols/kw1281.py:227-230` | `adaptation_save` inventava um resultado de sucesso (`{"channel", "value"}` pedidos) quando a centralina só respondia ACK; a UI mostrava "Canal gravado com o valor X" sem confirmação. | Corrigido |
| A2 | `session.py:144-148`, `ui/main_window.py:521-524` | "Codificação aceite pelo controlador" sem comparar a codificação devolvida com a pedida. Uma centralina que recusa devolve a identificação com a codificação antiga — o programa dizia "aceite". | Corrigido |
| A3 | `report.py:27-31`, `ui_score.py:7-8` | O relatório dizia "Nenhuma avaria registada nos controladores lidos" e dava pontuação de saúde mesmo com **0 controladores lidos**, com controladores sem comunicação, ou com o Auto-Scan **interrompido** (o "interrompido" não chegava ao relatório nem ao histórico). | Corrigido |
| A4 | `history.py`, `report.py`, `session.py` | Sessões e relatórios **não distinguiam simulador de interface real**. O próprio CHANGELOG 1.1.0 regista que leituras "bem-sucedidas" no histórico vinham do simulador. Um relatório gerado em simulação parecia um diagnóstico real. | Corrigido |

### MÉDIO

| # | Ficheiro:linhas | Problema | Estado |
|---|---|---|---|
| M1 | `ui/pages/module.py:152-157` | Repor revisão: `adaptation_test` e `adaptation_save` eram postos na fila juntos — o **save corria mesmo que o teste fosse recusado**. | Corrigido (`ECUSession.service_reset`) |
| M2 | `ui/pages/module.py:331, 614-620, 704-707` | Testes de saídas e ajuste básico arrancavam sem confirmação; o canal 00 (repõe **todas** as adaptações) tinha a mesma pergunta que qualquer outro canal. | Corrigido |
| M3 | `ui/main_window.py:525-526`, `kw1281.py:232-235` | "Login aceite": o KW1281 só confirma a receção (ACK); não indica se o código está certo. | Corrigido ("Login enviado…") |
| M4 | `worker.py:99-113` | Keep-alive recusado (resposta negativa) não actualizava `last` → repetido em ciclo apertado. **Medido: 30 pedidos em 1,1 s** com intervalo de 0,2 s (deviam ser ~5), e um traceback por pedido no `erros.log`. | Corrigido + teste |
| M5 | `session.py:122-124`, `worker.py:415-437` | Apagar avarias: se o pedido era aceite mas a releitura falhava, o erro aparecia como se o apagar tivesse falhado. Resultado real desconhecido. | Corrigido (`OperationUnconfirmed`, estado "por confirmar") |
| M6 | `kw1281.py:247-255` | Teste de saídas: uma resposta inesperada era tratada como "fim do teste". | Corrigido (erro explícito) |
| M7 | `ui/main_window.py:402-407` | Exportar o relatório de um Auto-Scan gravava **uma segunda sessão** no histórico (o Auto-Scan já fica gravado ao terminar) → duplicados e estatísticas inflacionadas. | Corrigido (`history.update_session`) |
| M8 | `report.py:21`, `ui/main_window.py:409-410` | Relatório refeito a partir do histórico saía com a **data de hoje** em vez da data do diagnóstico. | Corrigido |
| M9 | `j2534_bridge.py:115` | `n.value == 0` era testado antes do código de erro: interface J2534 desligada / erro do driver aparecia como "o controlador não respondeu". | Corrigido + teste |
| M10 | `j2534.py:137`, `d2xx.py:136` | Uma linha não-JSON vinda da ponte (ex.: DLL J2534 que escreve no stdout) dava `JSONDecodeError` → "Erro interno" e a conversa ficava dessincronizada. | Corrigido (erro da interface, ponte fechada) + teste |
| M11 | `ui/main_window.py:313-315` | "Interface pronta: COMx" logo ao escolher a porta, sem ter comunicado com nada. | Corrigido ("Interface escolhida") |
| M12 | `ui/pages/home.py:216` | Últimos veículos: "sem avarias" em sessões onde nenhum controlador foi lido. | Corrigido |

### BAIXO

| # | Ficheiro:linhas | Problema | Estado |
|---|---|---|---|
| B1 | `ui/pages/history.py:147-151` | Matrícula e descrições inseridas em HTML (rich text) sem escape. | Corrigido |
| B2 | `report.py:62`, `ui/pages/common.py:141` | "Causas prováveis" apresentadas sem indicar que são sugestão do programa. | Corrigido ("Possíveis causas — sugestão do programa") |
| B3 | `protocols/kw1281.py:11` | `import time` não usado. | Corrigido |
| B4 | `worker.py:60-69` | Se a thread não terminar em 12 s ao fechar, a janela fecha com a `QThread` ainda viva (Qt avisa/pode abortar). Só acontece com um driver bloqueado. | Corrigido (`Worker.stop()` fecha a interface à força) + teste |
| B5 | `j2534.py:125`, `d2xx.py:124` | `readline()` sem timeout: um driver que bloqueie dentro de `PassThruReadMsgs`/`FT_Read` bloqueia a thread de comunicação. | Corrigido (`rad/bridge.py`: thread de leitura e tempo máximo por pedido) + teste |
| B6 | `tests/test_usb_transports.py:10` | `import collections` não usado. | Corrigido |

### Por verificar (precisa de carro ou de documentação)

- **KWP2000 — byte de estado das avarias** (`kwp2000.py:165`): é descodificado com a mesma tabela do KW1281
  (`vag_data.decode_fault`). Nos VAG KWP2000 o significado dos bits pode diferir; confirmar num carro com
  centralina KWP2000 e avarias conhecidas.
- **KW1281 — resposta ao login**: algumas centralinas respondem NAK a um código errado, outras ACK. O programa
  já não afirma que foi aceite.
- **KW1281 — resposta à gravação de adaptação**: assume-se que a centralina devolve o canal/valor gravado num bloco
  0xE6 (como o simulador). Se uma centralina real só responder ACK, o programa mostra "resultado desconhecido" e
  pede para ler o canal — comportamento seguro, mas a confirmar no carro.
- **Fórmulas de medição** 4/27 (APMS/AAPMS) e outras raras em `vag_data.py:352-423`: não verificadas contra uma
  fonte; precisam de leitura comparativa num carro.

## 4. Protocolos — o que funciona realmente

| Função | KW1281 (cabo KKL) | KWP2000 (KKL) | KWP2000 (J2534) |
|---|---|---|---|
| Identificação | Implementada; testada no simulador | Implementada (0x1A 0x9B); simulador | Implementada; simulador J2534 |
| Ler avarias | Implementada; simulador | Implementada (0x18); simulador | Implementada; simulador J2534 |
| Apagar avarias | Implementada + releitura de confirmação | Implementada (0x14) + releitura | Implementada + releitura |
| Blocos de medição / dados em tempo real | Implementada (0x29), até 3 grupos | Implementada (0x21) | Implementada |
| Ajuste básico | Implementada (0x28), com confirmação | Não implementada (`NotSupported`) | Não implementada |
| Adaptação | Ler / testar / gravar com verificação do valor devolvido | Não implementada | Não implementada |
| Codificação | Implementada com verificação da codificação devolvida | Não implementada | Não implementada |
| Login | Envio; o protocolo não confirma o código | Não implementada | Não implementada |
| Teste de saídas | Implementada, com confirmação | Não implementada | Não implementada |
| Acesso de segurança (seed/key) | — | Não implementado | Não implementado |
| CAN / UDS | Não implementado | — | — |

**Nenhuma destas funções foi validada num veículo nesta auditoria** — todas foram exercitadas contra o simulador.
O histórico do projecto não tem nenhum registo verificado de leitura real (o cabo testado era um HEX-USB+CAN em
modo inteligente; ver `docs/HEX_USB.md`).

## 5. Interfaces

| Interface | Estado real |
|---|---|
| KKL 409.1 (FTDI/CH340, porta COM) | Implementada. Sem validação registada em carro. |
| Clone HEX-USB+CAN (0403:FA24) por D2XX ou WinUSB | O programa **fala com o microcontrolador do cabo** (versão, modo, teste da linha K — verificado no cabo real a 19/10/2026). **Não lê centralinas**: falta o protocolo de linha K do próprio microcontrolador. Não é anunciado como funcional. |
| HEX-V2 / HEX-NET genuínas | Não suportadas (firmware fechado). A detecção diz isso. |
| J2534 04.04 | KWP2000 sobre ISO 14230 com init a 5 baud. KW1281 recusado (correcto: a norma não permite os tempos por byte). Testado só com o simulador J2534. |

Detecção USB ≠ porta aberta ≠ comunicação com ECU: o Diagnóstico da ligação já separa estes passos
(`worker.py:308-382`) e a página inicial deixou de dizer "pronta" só por a porta estar escolhida.

## 6. Recomendações seguintes (não implementadas nesta ronda)

1. **Validação no carro** (prioridade máxima): um cabo KKL 409.1 com FTDI, num Golf IV TDI: ler 01/17/03, medir
   grupo 001, apagar avarias. Registar o resultado no CHANGELOG antes de anunciar compatibilidade.
2. ~~Leitura com timeout nas pontes (B5) e encerramento seguro da thread (B4).~~ Feito na 1.3.0.
3. Clientes/veículos: o histórico guarda matrícula/cliente/modelo em cada sessão; uma tabela própria de veículos
   (com VIN e pesquisa por VIN) evitaria repetir os dados — migração simples na mesma `historico.db`.
4. Relatório em duas camadas (técnico / cliente) a partir dos mesmos dados, com pré-visualização.
5. Redesenho visual mais profundo: só depois de os testes de UI correrem num ambiente com PySide6 (nesta ronda
   as alterações de interface foram mínimas, porque não puderam ser testadas aqui).
6. CAN/UDS como protocolos novos ao lado de `protocols/`, com um adaptador próprio — sem misturar com o K-line.

## 7. Prontidão para outros PCs (21/10/2026)

| # | Problema | Estado |
|---|---|---|
| P1 | Executável em `build\main.dist` era da v1.0.2 e nunca tinha sido verificado | `build_release.bat` apaga o build anterior e corre `--selftest` no `.exe`; sem OK não cria o instalador |
| P2 | `run.bat` precisa de Python e internet | Documentado: só para desenvolvimento; nas oficinas usa-se o instalador (sem Python nem internet) |
| P3 | Dependências sem versão fixa e PySide6 completo (+175 MB) | Versões fixas; `PySide6-Essentials`; `requirements-build.txt` |
| P4 | Falha no arranque fechava o programa sem mensagem nem `crash.log` | Corrigido + testes (`tests/test_startup.py`) |
| P5 | "Detectar cabo" congelava a janela | Corre em segundo plano + teste (`tests/test_options_detect.py`) |
| P6 | Nomes do PowerShell com acentos corrompidos | UTF-8 forçado + teste |

Por validar: build do instalador 1.3.0 e instalação limpa (Windows Sandbox / VM / outro PC sem Python).
