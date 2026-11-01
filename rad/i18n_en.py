"""Catálogo inglês da interface: texto de origem em português → inglês.

Mantido com tools/i18n_check.py (lista os textos sem tradução). Os marcadores {nome} e as etiquetas
HTML têm de ser iguais aos do texto de origem; tests/test_i18n.py confirma."""
# flake8: noqa: E501
EN = {
    "A ponte {name} parou: {e}":
        "The {name} bridge stopped: {e}",
    "A ponte {name} não respondeu em {timeout:.0f} s (pedido '{v}'): o driver da interface bloqueou. Desligue e volte a ligar o cabo.":
        "The {name} bridge did not answer within {timeout:.0f} s (request '{v}'): the interface driver hung. Unplug the cable and plug it back in.",
    "A ponte {name} terminou inesperadamente":
        "The {name} bridge ended unexpectedly",
    "Resposta inválida da ponte {name}: {v!r}":
        "Invalid answer from the {name} bridge: {v!r}",
    "{name} — driver RT-USB sem RT-USB.DLL":
        "{name} — RT-USB driver without RT-USB.DLL",
    "O driver está instalado mas falta a biblioteca RT-USB.DLL. Reinstale o driver, ou troque-o pelo WinUSB com o Zadig para usar o acesso USB directo. ":
        "The driver is installed but the RT-USB.DLL library is missing. Reinstall the driver, or replace it with WinUSB using Zadig to use direct USB access. ",
    "{name} — driver RT-USB OK, falta o componente de {bits} bits do programa":
        "{name} — RT-USB driver OK, the program's {bits}-bit component is missing",
    "O {dll} é de {bits} bits e é carregado pelo componente de {bits} bits que vem com o Roots Auto Doctor (pasta runtime/py{bits}), que não foi encontrado. Volte a instalar o programa (ou, no código-fonte, execute o run.bat) e carregue outra vez em Detectar cabo. ":
        "{dll} is {bits}-bit and is loaded by the {bits}-bit component that ships with Roots Auto Doctor (runtime/py{bits} folder), which was not found. Reinstall the program (or, from source code, run run.bat) and click Detect cable again. ",
    "{name} pronta pelo driver RT-USB ({chip}, S/N {v})":
        "{name} ready through the RT-USB driver ({chip}, S/N {v})",
    "Usa a biblioteca D2XX do driver (o VCDS continua a funcionar). Faça o Diagnóstico da ligação com o cabo no carro e a ignição ligada. ":
        "Uses the driver's D2XX library (VCDS keeps working). Run the Connection check with the cable in the car and the ignition on. ",
    "Estes clones (HEX-USB+CAN) têm um microcontrolador entre o chip FTDI e a ficha OBD: o Diagnóstico da ligação fala com ele, confirma que responde e põe-no em modo KKL para chegar à linha K. Faça-o com o cabo no carro e a ignição ligada.":
        "These clones (HEX-USB+CAN) have a microcontroller between the FTDI chip and the OBD connector: the Connection check talks to it, confirms it answers and switches it to KKL mode to reach the K-line. Do it with the cable in the car and the ignition on.",
    "{name} — chip {chip}, VID {vid} PID {pid}, sem driver":
        "{name} — chip {chip}, VID {vid} PID {pid}, no driver",
    "Esta interface não tem porta COM. Para o Roots Auto Doctor a usar por acesso USB directo, instale o driver WinUSB com o Zadig: Options → List All Devices → escolha '{name}' → WinUSB → Install Driver. Depois carregue de novo em Detectar cabo. (O VCDS deixa de reconhecer esta interface enquanto tiver o WinUSB.) ":
        "This interface has no COM port. For Roots Auto Doctor to use it through direct USB access, install the WinUSB driver with Zadig: Options → List All Devices → choose '{name}' → WinUSB → Install Driver. Then click Detect cable again. (VCDS stops recognising this interface while it has WinUSB.) ",
    "{name} — usa o driver '{v}'":
        "{name} — uses the '{v}' driver",
    "Este driver é o do programa do fabricante e o Roots Auto Doctor não o usa. Para acesso USB directo substitua-o pelo WinUSB com o Zadig (pode voltar ao driver anterior no Gestor de Dispositivos → Controlador → Reverter). ":
        "This driver belongs to the manufacturer's program and Roots Auto Doctor does not use it. For direct USB access replace it with WinUSB using Zadig (you can go back to the previous driver in Device Manager → Driver → Roll Back). ",
    "{name} — driver WinUSB OK, falta o pyftdi":
        "{name} — WinUSB driver OK, pyftdi is missing",
    "Instale as dependências: .venv\\Scripts\\python.exe -m pip install -r requirements.txt":
        "Install the dependencies: .venv\\Scripts\\python.exe -m pip install -r requirements.txt",
    "{name} pronta por USB directo ({chip}, S/N {v})":
        "{name} ready through direct USB ({chip}, S/N {v})",
    "Faça o Diagnóstico da ligação com o cabo no carro e a ignição ligada para confirmar que chega à linha K. ":
        "Run the Connection check with the cable in the car and the ignition on to confirm it reaches the K-line. ",
    "Interface {kind} ({v})":
        "{kind} interface ({v})",
    "Esta interface tem um microcontrolador com firmware {who} entre o USB e o carro, e só fala com o programa desse fabricante. Não funciona como cabo KKL e não pode ser usada pelo Roots Auto Doctor, mesmo com drivers. É preciso um cabo KKL 'VAG-COM 409.1' (FTDI ou CH340); para módulos KWP2000 também serve uma interface J2534.":
        "This interface has a microcontroller with {who} firmware between the USB and the car, and only talks to that manufacturer's program. It does not work as a KKL cable and cannot be used by Roots Auto Doctor, even with drivers. You need a 'VAG-COM 409.1' KKL cable (FTDI or CH340); a J2534 interface also works for KWP2000 modules.",
    "Cabo {chip} pronto em {com} — Latency Timer {lat} ms":
        "{chip} cable ready on {com} — Latency Timer {lat} ms",
    "Funciona, mas a leitura será lenta. Gestor de Dispositivos → Portas (COM e LPT) → {com} → Propriedades → Definições da porta → Avançadas → Latency Timer = 1.":
        "It works, but reading will be slow. Device Manager → Ports (COM & LPT) → {com} → Properties → Port Settings → Advanced → Latency Timer = 1.",
    "Cabo {chip} pronto em {com}":
        "{chip} cable ready on {com}",
    "Cabo FTDI sem porta COM":
        "FTDI cable without a COM port",
    "O driver está instalado mas a porta COM está desligada. Gestor de Dispositivos → Controladores USB → USB Serial Converter → Propriedades → Avançadas → marque 'Load VCP' → OK, e volte a ligar o cabo. Se não existir essa opção, instale o driver VCP da FTDI.":
        "The driver is installed but the COM port is disabled. Device Manager → Universal Serial Bus controllers → USB Serial Converter → Properties → Advanced → tick 'Load VCP' → OK, and plug the cable in again. If that option does not exist, install FTDI's VCP driver.",
    "Cabo {chip} sem driver":
        "{chip} cable without a driver",
    "Instale o driver oficial ({vendor}) e volte a ligar o cabo.":
        "Install the official driver ({vendor}) and plug the cable in again.",
    "Ligado a {where}":
        "Connected to {where}",
    "Ligado a {where} — {name}":
        "Connected to {where} — {name}",
    "A ligar ao controlador {where}…":
        "Connecting to module {where}…",
    "{e} (o {v} da interface é de {bits} bits)":
        "{e} (the interface's {v} is {bits}-bit)",
    "Não foi encontrado o RT-USB.DLL do driver da interface. Reinstale o driver ou use o acesso USB directo (WinUSB).":
        "The interface driver's RT-USB.DLL was not found. Reinstall the driver or use direct USB access (WinUSB).",
    "Código OBD":
        "OBD code",
    "Categoria do código: {cat}.":
        "Code category: {cat}.",
    "Pendente: a centralina detectou a falha num ciclo de condução, mas ainda não a confirmou.":
        "Pending: the ECU detected the fault during a drive cycle but has not confirmed it yet.",
    "Permanente: só desaparece quando a própria centralina confirmar a reparação (não se apaga pelo programa).":
        "Permanent: it only goes away when the ECU itself confirms the repair (the program cannot clear it).",
    "As causas dependem do fabricante e do motor: consulte a documentação técnica do veículo.":
        "Causes depend on the manufacturer and the engine: check the vehicle's technical documentation.",
    "Intermitente: a avaria não está presente neste momento. Apague e faça um teste de estrada; se voltar, investigue as causas abaixo.":
        "Intermittent: the fault is not present right now. Clear it and do a road test; if it comes back, investigate the causes below.",
    "Porta USB inválida: {port}":
        "Invalid USB port: {port}",
    "Falta o pyusb. Instale com: pip install pyftdi libusb-package":
        "pyusb is missing. Install it with: pip install pyftdi libusb-package",
    "libusb-1.0 não encontrado. Instale com: pip install libusb-package":
        "libusb-1.0 not found. Install it with: pip install libusb-package",
    "USB directo — {name} [{chip}, VID {vid:04X} PID {pid:04X}{v}]":
        "Direct USB — {name} [{chip}, VID {vid:04X} PID {pid:04X}{v}]",
    "Falta o pyftdi. Instale com: pip install pyftdi libusb-package":
        "pyftdi is missing. Install it with: pip install pyftdi libusb-package",
    "{port}: interface fechada":
        "{port}: interface closed",
    "{what}: {e} — o cabo foi desligado?":
        "{what}: {e} — was the cable unplugged?",
    "Não foi possível configurar o chip FTDI: {e}":
        "Could not configure the FTDI chip: {e}",
    "Sem dados suficientes":
        "Not enough data",
    "Cilindro {v}: {v2}{v3} mg/H{v4}":
        "Cylinder {v}: {v2}{v3} mg/H{v4}",
    "Cilindro(s) {v} fora de ±{v2} mg/H. Pode indicar injector a pingar/gasto ou compressão baixa nesse cilindro.":
        "Cylinder(s) {v} outside ±{v2} mg/H. This may point to a dripping/worn injector or low compression on that cylinder.",
    "Todos os cilindros dentro de ±{v} mg/H.":
        "All cylinders within ±{v} mg/H.",
    "Não houve aceleração suficiente acima de 2000 rpm. Repita o teste.":
        "There was not enough acceleration above 2000 rpm. Repeat the test.",
    "{v} leituras, {v2} acima de 2000 rpm":
        "{v} readings, {v2} above 2000 rpm",
    "Pressão abaixo da pretendida. Verifique fugas na admissão/intercooler, tubos de vácuo, N75 e o turbo.":
        "Pressure below the specified value. Check for leaks in the intake/intercooler, vacuum hoses, N75 and the turbo.",
    "Pressão acima da pretendida (sobrepressão). Verifique N75, geometria variável/wastegate e o sensor de pressão.":
        "Pressure above the specified value (overboost). Check N75, variable geometry/wastegate and the pressure sensor.",
    "A pressão real acompanha a pretendida.":
        "Actual pressure follows the specified pressure.",
    "A massa de ar real fica abaixo da pretendida. Pode indicar medidor (MAF) fraco, filtro de ar sujo, fuga antes do MAF ou EGR a abrir em carga.":
        "Actual air mass stays below the specified value. This may point to a weak air mass meter (MAF), a dirty air filter, a leak before the MAF or the EGR opening under load.",
    "A massa de ar real acompanha a pretendida.":
        "Actual air mass follows the specified air mass.",
    "{baud}: velocidade recusada ({e})":
        "{baud}: baud rate refused ({e})",
    "O cabo não respondeu ao pedido de modo (ReadBoot): não é seguro enviar a mudança":
        "The cable did not answer the mode request (ReadBoot): it is not safe to send the change",
    "O cabo não confirmou a mudança de modo (resposta: {v})":
        "The cable did not confirm the mode change (answer: {v})",
    "O cabo confirmou, mas o modo lido a seguir é {v}":
        "The cable confirmed, but the mode read afterwards is {v}",
    "sessão {sid} não encontrada":
        "session {sid} not found",
    "Esta interface usa um driver de {want} bits e falta o componente de {want} bits do programa (pasta runtime/py{want}): {where}.":
        "This interface uses a {want}-bit driver and the program's {want}-bit component is missing (runtime/py{want} folder): {where}.",
    "Interface J2534 não está aberta":
        "J2534 interface is not open",
    "Driver J2534 não encontrado: {dll}":
        "J2534 driver not found: {dll}",
    "O controlador não respondeu (timeout J2534)":
        "The module did not answer (J2534 timeout)",
    "Tipo de alteração desconhecido: {kind}":
        "Unknown change type: {kind}",
    "Estado de alteração inválido: {status}":
        "Invalid change status: {status}",
    "Codificação: {before} → {after}":
        "Coding: {before} → {after}",
    "Adaptação canal {channel:02d}: {before} → {after}":
        "Adaptation channel {channel:02d}: {before} → {after}",
    " (por confirmar)":
        " (unconfirmed)",
    "Simulador J2534 (sem carro) — testa a ligação por PassThru":
        "J2534 simulator (no car) — tests the PassThru connection",
    "Não foi possível abrir a porta {port_name}: {e}":
        "Could not open port {port_name}: {e}",
    "Não foi possível mudar a velocidade da porta: {e}":
        "Could not change the port baud rate: {e}",
    "{port_name}: a porta está fechada":
        "{port_name}: the port is closed",
    "Erro de leitura na porta: {e}":
        "Port read error: {e}",
    "Sem resposta do controlador ({what})":
        "No answer from the module ({what})",
    "Erro de escrita na porta: {e}":
        "Port write error: {e}",
    "Eco não recebido — verifique o cabo e a ignição":
        "Echo not received — check the cable and the ignition",
    "Colisão na linha K: enviado {expected:02X}, eco {b:02X}":
        "K-line collision: sent {expected:02X}, echo {b:02X}",
    "Erro na porta durante o init a 5 baud: {e}":
        "Port error during the 5-baud init: {e}",
    "Operação cancelada":
        "Operation cancelled",
    "Erro de escrita: {e}":
        "Write error: {e}",
    "Eco do complemento KB2 não recebido":
        "KB2 complement echo not received",
    "Erro na porta durante o teste de eco: {e}":
        "Port error during the echo test: {e}",
    "O licenciamento ainda não está configurado nesta versão.":
        "Licensing is not configured in this version yet.",
    "Isto não é uma chave de licença do Roots Auto Doctor.":
        "This is not a Roots Auto Doctor licence key.",
    "A chave está incompleta ou foi mal copiada.":
        "The key is incomplete or was copied incorrectly.",
    "A chave não é válida (assinatura errada ou chave alterada).":
        "The key is not valid (wrong signature or altered key).",
    "A chave não é válida.":
        "The key is not valid.",
    "Esta licença é de outro PC ({other}). O ID deste PC é {machine}.":
        "This licence belongs to another PC ({other}). This PC's ID is {machine}.",
    "A licença expirou em {date}.":
        "The licence expired on {date}.",
    "Licenciamento não configurado (versão de desenvolvimento).":
        "Licensing not configured (development version).",
    "Modo demonstração: sem licença activada neste PC.":
        "Demo mode: no licence activated on this PC.",
    "Modo demonstração: {reason}":
        "Demo mode: {reason}",
    "Licenciado a {workshop}, válida até {date}.":
        "Licensed to {workshop}, valid until {date}.",
    "Licenciado a {workshop}, sem data de fim.":
        "Licensed to {workshop}, no end date.",
    "Modo demonstração: esta função escreve no veículo e precisa de uma licença. Active a licença em Opções → Licença (o simulador funciona sem limites).":
        "Demo mode: this function writes to the vehicle and needs a licence. Activate the licence in Options → Licence (the simulator works without limits).",
    "específico do fabricante":
        "manufacturer-specific",
    "genérico (normalizado)":
        "generic (standardised)",
    "tipo de falha 0x{ftb:02X}":
        "failure type 0x{ftb:02X}",
    "Erro de escrita na porta {port_name}: {e}":
        "Write error on port {port_name}: {e}",
    "Erro de leitura na porta {port_name}: {e}":
        "Read error on port {port_name}: {e}",
    "O adaptador deixou de responder (sem resposta a {cmd!r} na porta {port_name})":
        "The adapter stopped answering (no answer to {cmd!r} on port {port_name})",
    "O adaptador não suporta o comando {cmd}":
        "The adapter does not support the command {cmd}",
    "O adaptador indicou um protocolo desconhecido: {dpn!r}":
        "The adapter reported an unknown protocol: {dpn!r}",
    "Ainda não há protocolo com o veículo (ligue primeiro)":
        "No protocol with the vehicle yet (connect first)",
    "Pedidos dirigidos a uma centralina só estão disponíveis em CAN nesta versão":
        "Requests addressed to a single ECU are only available on CAN in this version",
    "Sem resposta válida ao pedido {cmd}":
        "No valid answer to request {cmd}",
    "mensagem vazia":
        "empty message",
    "trama vazia":
        "empty frame",
    "tipo de trama ISO-TP inválido (PCI 0x{v:02X})":
        "invalid ISO-TP frame type (PCI 0x{v:02X})",
    "Single Frame CAN-FD curta":
        "Short CAN-FD Single Frame",
    "Single Frame com comprimento {n} e {v} byte(s) de dados":
        "Single Frame with length {n} and {v} data byte(s)",
    "First Frame com menos de 8 bytes":
        "First Frame with fewer than 8 bytes",
    "First Frame com comprimento {n} (mínimo 8)":
        "First Frame with length {n} (minimum 8)",
    "Consecutive Frame sem First Frame":
        "Consecutive Frame without a First Frame",
    "Consecutive Frame fora de sequência (esperado {exp}, recebido {seq})":
        "Consecutive Frame out of sequence (expected {exp}, received {seq})",
    "Flow Control inesperado":
        "Unexpected Flow Control",
    "Erro ao enviar na interface CAN: {e}":
        "Error sending on the CAN interface: {e}",
    "Erro ao ler da interface CAN: {e}":
        "Error reading from the CAN interface: {e}",
    "A centralina {rx_id:03X} não enviou Flow Control":
        "ECU {rx_id:03X} did not send Flow Control",
    "A centralina {rx_id:03X} recusou a mensagem (transbordo do buffer)":
        "ECU {rx_id:03X} refused the message (buffer overflow)",
    "Pedidos funcionais têm de caber numa única trama":
        "Functional requests must fit in a single frame",
    "Nenhuma centralina respondeu no barramento CAN":
        "No ECU answered on the CAN bus",
    "Nenhuma centralina respondeu ao pedido OBD-II 01 00":
        "No ECU answered the OBD-II 01 00 request",
    "PID 0x{pid:02X} inesperado na resposta":
        "Unexpected PID 0x{pid:02X} in the answer",
    "PID 0x{pid:02X}: resposta curta":
        "PID 0x{pid:02X}: short answer",
    "sem definição no programa":
        "not defined in the program",
    "não suportado por esta centralina":
        "not supported by this ECU",
    "sem resposta da centralina":
        "no answer from the ECU",
    "recusado: NRC 0x{nrc:02X}":
        "refused: NRC 0x{nrc:02X}",
    "resposta inválida":
        "invalid answer",
    "Nenhuma centralina respondeu ao modo {service:02X} ({kind})":
        "No ECU answered mode {service:02X} ({kind})",
    "Sem resposta válida ao modo {service:02X}":
        "No valid answer to mode {service:02X}",
    "Nenhuma centralina confirmou o pedido de apagar avarias":
        "No ECU confirmed the request to clear faults",
    "PID {pid:02X}: esperava {size} byte(s), recebeu {n}":
        "PID {pid:02X}: expected {size} byte(s), received {n}",
    "tipo {n}":
        "type {n}",
    "compressão (diesel)":
        "compression (diesel)",
    "faísca (gasolina)":
        "spark (petrol)",
    "PID {pid:02X} (sem definição no programa)":
        "PID {pid:02X} (not defined in the program)",
    "O pedido de apagar foi aceite por {v}, mas não foi possível voltar a ler as avarias ({e}). Leia novamente para confirmar.":
        "The clear request was accepted by {v}, but the faults could not be read again ({e}). Read them again to confirm.",
    "UDS só está disponível em veículos com CAN (ISO 15765)":
        "UDS is only available on vehicles with CAN (ISO 15765)",
    "A centralina {target} não respondeu a nenhum identificador UDS normalizado":
        "ECU {target} did not answer any standard UDS identifier",
    "Não há ligação ao veículo":
        "No connection to the vehicle",
    "UDS precisa de uma ligação CAN (ISO 15765)":
        "UDS needs a CAN connection (ISO 15765)",
    "A centralina {target} não deu resposta válida ao serviço 0x{sid:02X}":
        "ECU {target} gave no valid answer to service 0x{sid:02X}",
    "Só as sessões normal (01) e alargada (03) são permitidas":
        "Only the default (01) and extended (03) sessions are allowed",
    "Resposta inválida ao pedido de sessão":
        "Invalid answer to the session request",
    "Resposta ao identificador {did:04X} com formato inválido":
        "Answer to identifier {did:04X} has an invalid format",
    "Resposta inválida ao pedido de contagem de avarias":
        "Invalid answer to the fault count request",
    "Resposta inválida ao pedido de avarias":
        "Invalid answer to the fault request",
    "Sem complemento do byte {b:02X}":
        "No complement for byte {b:02X}",
    "Complemento errado: enviado {b:02X}, recebido {c:02X}":
        "Wrong complement: sent {b:02X}, received {c:02X}",
    "O controlador não enviou bloco (timeout)":
        "The module did not send a block (timeout)",
    "Comprimento de bloco inválido: {length:02X}":
        "Invalid block length: {length:02X}",
    "Bloco incompleto (timeout)":
        "Incomplete block (timeout)",
    "Fim de bloco inválido: {v:02X}":
        "Invalid block end: {v:02X}",
    "O controlador recusou o pedido (NAK)":
        "The module refused the request (NAK)",
    "Demasiados blocos de identificação":
        "Too many identification blocks",
    "Grupo {group:03d} sem dados":
        "Group {group:03d} has no data",
    "Resposta inesperada ao grupo {group:03d}: {blk}":
        "Unexpected answer to group {group:03d}: {blk}",
    "Resposta de adaptação inválida":
        "Invalid adaptation answer",
    "A codificação tem de estar entre 00000 e 32767":
        "Coding must be between 00000 and 32767",
    "Resposta inesperada ao teste de saídas: {v}":
        "Unexpected answer to the output test: {v}",
    "O controlador não respondeu (timeout KWP2000)":
        "The module did not answer (KWP2000 timeout)",
    "Checksum KWP2000 inválido":
        "Invalid KWP2000 checksum",
    "Tempo esgotado à espera de resposta":
        "Timed out waiting for an answer",
    "Mensagem J2534 vazia":
        "Empty J2534 message",
    "Mensagem J2534 curta":
        "Short J2534 message",
    "Mensagem J2534 incompleta":
        "Incomplete J2534 message",
    "Nenhum controlador foi lido: não é possível avaliar o estado do veículo.":
        "No module was read: the condition of the vehicle cannot be assessed.",
    "Foi encontrada 1 avaria em {n_mod} controlador(es).":
        "1 fault was found in {n_mod} module(s).",
    "Foram encontradas {n} avarias em {n_mod} controlador(es).":
        "{n} faults were found in {n_mod} module(s).",
    "Nenhuma avaria registada nos {n} controlador(es) lido(s).":
        "No faults stored in the {n} module(s) read.",
    "{n} controlador(es) não comunicaram e não foram avaliados.":
        "{n} module(s) did not communicate and were not assessed.",
    "O Auto-Scan foi interrompido: o resultado é parcial.":
        "The Auto-Scan was interrupted: the result is partial.",
    "<b>DADOS SIMULADOS</b> — este relatório foi gerado com o simulador do programa e não corresponde a nenhum veículo real.":
        "<b>SIMULATED DATA</b> — this report was generated with the program's simulator and does not correspond to any real vehicle.",
    "<b>VERSÃO DE DEMONSTRAÇÃO</b> — relatório gerado sem licença do {app}.":
        "<b>DEMO VERSION</b> — report generated without a {app} licence.",
    "Sem comunicação: {error}":
        "No communication: {error}",
    "Erro":
        "Error",
    "1 avaria":
        "1 fault",
    "{n} avarias":
        "{n} faults",
    "intermitente":
        "intermittent",
    "permanente":
        "permanent",
    "Possíveis causas (sugestão do programa, a confirmar pelo técnico): {causes}.":
        "Possible causes (suggested by the program, to be confirmed by the technician): {causes}.",
    "Confirmada":
        "Confirmed",
    "Por confirmar":
        "Unconfirmed",
    "Intervenções nos controladores":
        "Interventions on the modules",
    "Codificações e adaptações gravadas durante esta visita, com o valor anterior. \"Confirmada\" = o controlador devolveu o valor gravado.":
        "Codings and adaptations written during this visit, with the previous value. \"Confirmed\" = the module returned the written value.",
    "Observações":
        "Notes",
    "(leitura parcial)":
        "(partial reading)",
    "{n} controlador(es) lido(s)":
        "{n} module(s) read",
    "{n} sem comunicação":
        "{n} without communication",
    "Interface: {interface}":
        "Interface: {interface}",
    "Gerado por {app} v{version}. Os códigos de avaria e o seu estado são os que os controladores registaram no momento da leitura; a gravidade e as possíveis causas são sugestões do programa. O diagnóstico final cabe ao técnico. Controladores que não comunicaram não foram avaliados.":
        "Generated by {app} v{version}. Fault codes and their status are those stored by the modules at the time of reading; severity and possible causes are suggestions from the program. The final diagnosis is the technician's responsibility. Modules that did not communicate were not assessed.",
    "Cliente":
        "Customer",
    "Marca / modelo":
        "Make / model",
    "Matrícula":
        "Licence plate",
    "Quilómetros":
        "Mileage (km)",
    "Saúde do veículo: {score}/100":
        "Vehicle health: {score}/100",
    "Protocolo desconhecido (keyword {kw})":
        "Unknown protocol (keyword {kw})",
    "O controlador {address:02X} não responde (verifique ignição, cabo e endereço)":
        "Module {address:02X} does not answer (check ignition, cable and address)",
    "Sincronização falhou em todas as velocidades":
        "Synchronisation failed at every baud rate",
    "O pedido de apagar avarias foi aceite, mas não foi possível voltar a ler a memória para confirmar ({e}). Volte a ligar e leia as avarias.":
        "The request to clear faults was accepted, but the memory could not be read again to confirm ({e}). Reconnect and read the faults.",
    "O controlador não devolveu o valor {what}: o resultado é desconhecido. Leia o canal para confirmar.":
        "The module did not return the {what} value: the result is unknown. Read the channel to confirm.",
    "O controlador não aceitou o valor {val} no canal {ch:02d} (respondeu canal {v}, valor {v2}).":
        "The module did not accept the value {val} on channel {ch:02d} (answered channel {v}, value {v2}).",
    "O painel não aceitou o valor 0 no canal 02 — nada foi gravado. ({e})":
        "The instrument cluster did not accept the value 0 on channel 02 — nothing was saved. ({e})",
    "O painel não confirmou o valor de teste no canal 02 — nada foi gravado.":
        "The instrument cluster did not confirm the test value on channel 02 — nothing was saved.",
    "O controlador não devolveu a codificação: o resultado é desconhecido. Feche e volte a abrir o controlador para confirmar.":
        "The module did not return the coding: the result is unknown. Close and reopen the module to confirm.",
    "Codificação {coding:05d} confirmada pelo controlador.":
        "Coding {coding:05d} confirmed by the module.",
    "  Procurar…":
        "  Search…",
    "Controlador ligado":
        "Connected module",
    "Sem ligação":
        "Not connected",
    "MODO DE SIMULAÇÃO":
        "SIMULATION MODE",
    "MODO DEMONSTRAÇÃO":
        "DEMO MODE",
    "Sem licença: lê tudo, mas não escreve em carros reais. Clique para activar.":
        "No licence: reads everything but does not write to real cars. Click to activate.",
    "Nova versão disponível":
        "New version available",
    "Voltar a ligar":
        "Reconnect",
    "Registo de comunicação":
        "Communication log",
    "Registo técnico":
        "Technical log",
    "Modo demonstração ({e}).":
        "Demo mode ({e}).",
    "Nova versão {version} disponível":
        "New version {version} available",
    "Abre a página da versão nova no navegador.":
        "Opens the new version's page in the browser.",
    "Está disponível a versão {version}":
        "Version {version} is available",
    "Versão instalada: {VERSION}\nVersão nova: {v}\n\n":
        "Installed version: {VERSION}\nNew version: {v}\n\n",
    "Abrir a página para descarregar o instalador?":
        "Open the page to download the installer?",
    "Início":
        "Home",
    "Página inicial":
        "Home page",
    "Controladores":
        "Control modules",
    "Escolher um módulo para ligar":
        "Choose a module to connect to",
    "Ver o último Auto-Scan e o mapa do veículo":
        "See the last Auto-Scan and the vehicle map",
    "Iniciar Auto-Scan":
        "Start Auto-Scan",
    "Ler todos os controladores agora":
        "Read all modules now",
    "Compatibilidade":
        "Compatibility",
    "Diagnósticos guardados":
        "Saved diagnostics",
    "Histórico":
        "History",
    "Opções":
        "Options",
    "Porta do cabo, oficina e suporte":
        "Cable port, workshop and support",
    "PDF ou página web":
        "PDF or web page",
    "Relatório para o cliente":
        "Customer report",
    "Abrir simulador":
        "Open simulator",
    "Experimentar sem carro":
        "Try it without a car",
    "Detectar cabo":
        "Detect cable",
    "Diagnóstico da ligação":
        "Connection check",
    "Mostrar ou esconder (Ctrl+L)":
        "Show or hide (Ctrl+L)",
    "Controlador ligado (F5)":
        "Connected module (F5)",
    "Ler avarias":
        "Read faults",
    "Controlador":
        "Module",
    "Ligar a {addr:02X} · {name}":
        "Connect to {addr:02X} · {name}",
    "Simulador activo: experimente 01 Motor, 03 ABS ou 17 Painel":
        "Simulator active: try 01 Engine, 03 ABS or 17 Instruments",
    "VIN lido do veículo: {vin}":
        "VIN read from the vehicle: {vin}",
    "porta por escolher":
        "port not chosen",
    " (simulação)":
        " (simulation)",
    "Escolha a porta do cabo em Opções":
        "Choose the cable port in Options",
    "Modo de simulação — os dados não vêm de um carro":
        "Simulation mode — the data does not come from a car",
    "Simulador":
        "Simulator",
    "Opções guardadas":
        "Options saved",
    "Escolha primeiro a porta do cabo em Opções.":
        "Choose the cable port in Options first.",
    "Aguarde — ainda a comunicar com o carro":
        "Please wait — still communicating with the car",
    "Escolha primeiro a porta do cabo (ou use Detectar cabo).":
        "Choose the cable port first (or use Detect cable).",
    "Endereço inválido.":
        "Invalid address.",
    "A verificar a ligação…":
        "Checking the connection…",
    "Vai repor o modo de arranque de origem (inteligente) do cabo. Continuar?":
        "This will restore the cable's original (smart) start-up mode. Continue?",
    "A falar com o cabo…":
        "Talking to the cable…",
    "<p><b>Ligação OK — pode usar o programa no carro.</b></p>":
        "<p><b>Connection OK — you can use the program on the car.</b></p>",
    "<p><b>A ligação falhou no passo assinalado.</b> Se não conseguir resolver, use <i>Pacote de suporte</i> em Opções e envie o ficheiro.</p>":
        "<p><b>The connection failed at the marked step.</b> If you cannot solve it, use <i>Support package</i> in Options and send the file.</p>",
    "Ainda não há dados para o relatório.\nFaça um Auto-Scan ou ligue a um controlador e leia as avarias.":
        "There is no data for the report yet.\nRun an Auto-Scan or connect to a module and read the faults.",
    "Registo de alterações: não foi possível ler ({e})":
        "Change log: could not be read ({e})",
    "Histórico: não foi possível guardar ({e})":
        "History: could not be saved ({e})",
    "Guardar relatório":
        "Save report",
    "Não foi possível gravar o relatório:\n{e}":
        "Could not save the report:\n{e}",
    "Relatório guardado":
        "Report saved",
    "A ligar…":
        "Connecting…",
    "Ligado":
        "Connected",
    "A ligar a {data:02X}…":
        "Connecting to {data:02X}…",
    "A ligar ao controlador {data:02X} — {v}…":
        "Connecting to module {data:02X} — {v}…",
    "Ligado a {address:02X}{sim}":
        "Connected to {address:02X}{sim}",
    "Ligação terminada: {data}":
        "Connection ended: {data}",
    "Controlador fechado":
        "Module closed",
    "Ligação ao controlador perdida":
        "Connection to the module lost",
    "Voltar a ligar a {last_address:02X}":
        "Reconnect to {last_address:02X}",
    "Memória de avarias apagada":
        "Fault memory cleared",
    "Apagado — {v} avaria(s) voltaram a aparecer":
        "Cleared — {v} fault(s) came back",
    "Sem avarias":
        "No faults",
    "{v} avaria(s) encontrada(s)":
        "{v} fault(s) found",
    "Revisão reposta — confirmado pelo painel":
        "Service reminder reset — confirmed by the instrument cluster",
    "Adaptação gravada — confirmada pelo controlador":
        "Adaptation saved — confirmed by the module",
    "Em {unknown} controlador(es) o pedido de apagar foi enviado mas não foi possível confirmar o resultado. Volte a fazer o Auto-Scan para ver o estado real.":
        "In {unknown} module(s) the clear request was sent but the result could not be confirmed. Run the Auto-Scan again to see the real state.",
    "Avarias apagadas em todos os controladores":
        "Faults cleared in all modules",
    "Feito — {left} avaria(s) voltaram a aparecer":
        "Done — {left} fault(s) came back",
    ", {v} controlador(es) por confirmar":
        ", {v} module(s) unconfirmed",
    "Auto-Scan concluído":
        "Auto-Scan finished",
    "Auto-Scan interrompido":
        "Auto-Scan interrupted",
    "Avarias apagadas — confirmado pela releitura":
        "Faults cleared — confirmed by reading again",
    "Pedido aceite, mas {left} avaria(s) continuam na memória":
        "Request accepted, but {left} fault(s) are still in memory",
    "ERRO ({cmd}): {msg}":
        "ERROR ({cmd}): {msg}",
    "Auto-Scan {i}/{total}: {address:02X} {module}":
        "Auto-Scan {i}/{total}: {address:02X} {module}",
    "Lê a identificação e as avarias de todos os controladores. Clique no mapa ou num mosaico para abrir o controlador.":
        "Reads the identification and faults of every module. Click the map or a tile to open the module.",
    "Diagnóstico completo":
        "Full diagnosis",
    "▶  Iniciar Auto-Scan":
        "▶  Start Auto-Scan",
    "Copiar":
        "Copy",
    "Guardar .txt":
        "Save .txt",
    "Apagar avarias em todos":
        "Clear faults in all",
    "MAPA DO VEÍCULO":
        "VEHICLE MAP",
    "Pronto para ler":
        "Ready to read",
    "Ligue a ignição e inicie o Auto-Scan.":
        "Switch the ignition on and start the Auto-Scan.",
    "Ainda não há resultados. Ligue a ignição e carregue em Iniciar Auto-Scan.":
        "No results yet. Switch the ignition on and click Start Auto-Scan.",
    "Endereço":
        "Address",
    "Estado":
        "Status",
    "Módulo / Avaria":
        "Module / Fault",
    "Seleccione uma avaria na lista para ver as causas prováveis.":
        "Select a fault in the list to see the probable causes.",
    "Não há avarias para apagar. Faça primeiro um Auto-Scan.":
        "There are no faults to clear. Run an Auto-Scan first.",
    "Apagar a memória de avarias em {v} controlador(es) ({names})?\n\nRecomenda-se gravar ou imprimir o relatório antes.":
        "Clear the fault memory in {v} module(s) ({names})?\n\nSaving or printing the report first is recommended.",
    "A apagar avarias…":
        "Clearing faults…",
    "Saúde do veículo: {text}":
        "Vehicle health: {text}",
    "Nenhum controlador lido.":
        "No module read.",
    "Avaria mais grave: {v}":
        "Most severe fault: {v}",
    " — {left} voltaram":
        " — {left} came back",
    "Avarias apagadas":
        "Faults cleared",
    " — {errs} sem comunicação":
        " — {errs} without communication",
    " — {unknown} por confirmar":
        " — {unknown} unconfirmed",
    "{v} módulo(s) · {nf} avaria(s)":
        "{v} module(s) · {nf} fault(s)",
    "  (interrompido)":
        "  (interrupted)",
    "  · SIMULAÇÃO":
        "  · SIMULATION",
    "A parar…":
        "Stopping…",
    "A ler os controladores…":
        "Reading the modules…",
    "A varrer o veículo":
        "Scanning the vehicle",
    "■  Parar":
        "■  Stop",
    "NOVA":
        "NEW",
    "Intermitente":
        "Intermittent",
    "Seleccione para ver as causas prováveis":
        "Select to see the probable causes",
    "Erro: ":
        "Error: ",
    "Concluído":
        "Finished",
    "Interrompido":
        "Interrupted",
    "Não foi possível ler":
        "Could not read",
    "Nenhum controlador respondeu. Confirme a ignição, o cabo e a porta nas Opções.":
        "No module answered. Check the ignition, the cable and the port in Options.",
    "Veja a explicação ao lado.":
        "See the explanation alongside.",
    "a última visita":
        "the last visit",
    "Desde {when}: sem avarias em nenhum dos diagnósticos.":
        "Since {when}: no faults in any of the diagnostics.",
    "<b style='color:{v}'>{n_new} nova(s)</b>":
        "<b style='color:{v}'>{n_new} new</b>",
    "<b style='color:{v}'>{n_res} resolvida(s)</b>":
        "<b style='color:{v}'>{n_res} resolved</b>",
    "<b style='color:{v}'>{n_keep} mantêm-se</b>":
        "<b style='color:{v}'>{n_keep} still present</b>",
    "Comparação com a visita de <b>{when}</b>:":
        "Comparison with the visit of <b>{when}</b>:",
    "<br><span style='color:%s'>Resolvidas: %s</span>":
        "<br><span style='color:%s'>Resolved: %s</span>",
    "{APP_NAME} v{VERSION} — Auto-Scan {v:%d/%m/%Y %H:%M}":
        "{APP_NAME} v{VERSION} — Auto-Scan {v:%d/%m/%Y %H:%M}",
    "*** DADOS SIMULADOS — não correspondem a nenhum veículo real ***":
        "*** SIMULATED DATA — does not correspond to any real vehicle ***",
    "Endereço {address:02X}: {module}":
        "Address {address:02X}: {module}",
    "   Peça: {part}   Componente: {component}":
        "   Part: {part}   Component: {component}",
    "   Codificação: {coding:05d}   WSC: {wsc}":
        "   Coding: {coding:05d}   WSC: {wsc}",
    "   {v} avaria(s)":
        "   {v} fault(s)",
    "   Erro: {v}":
        "   Error: {v}",
    "Texto (*.txt)":
        "Text (*.txt)",
    "Seleccione uma avaria para ver as causas prováveis e o que verificar.":
        "Select a fault to see the probable causes and what to check.",
    "ASSISTENTE DE DIAGNÓSTICO":
        "DIAGNOSTIC ASSISTANT",
    "<p style='margin:8px 0 2px 0'><b style='color:{CYAN}'>Possíveis causas</b> <span style='color:{MUTED}'>— sugestão do programa, confirme com medições</span></p><ul style='margin:0'>":
        "<p style='margin:8px 0 2px 0'><b style='color:{CYAN}'>Possible causes</b> <span style='color:{MUTED}'>— suggested by the program, confirm with measurements</span></p><ul style='margin:0'>",
    "<p style='margin:8px 0 2px 0'><b style='color:{CYAN}'>O que verificar</b></p><ul style='margin:0'>":
        "<p style='margin:8px 0 2px 0'><b style='color:{CYAN}'>What to check</b></p><ul style='margin:0'>",
    "<p style='color:{MUTED}; margin-top:6px'>Sem ficha específica para este código: use o tipo de avaria acima como ponto de partida e consulte a documentação do motor.</p>":
        "<p style='color:{MUTED}; margin-top:6px'>No specific sheet for this code: use the fault type above as a starting point and check the engine documentation.</p>",
    "Avaria {vag}":
        "Fault {vag}",
    "CAMPO {n}":
        "FIELD {n}",
    "fórmula {formula}  a={a}  b={b}":
        "formula {formula}  a={a}  b={b}",
    "Ler este grupo ({title})":
        "Read this group ({title})",
    "Grupo":
        "Group",
    "Grupo ":
        "Group ",
    "Testes: {tests}":
        "Tests: {tests}",
    "Detectar o cabo ≠ abrir a interface ≠ comunicar com uma centralina ≠ interpretar bem a resposta. Cada etapa tem o seu nível de prova; nenhum sobe sem a prova correspondente.":
        "Detecting the cable ≠ opening the interface ≠ communicating with an ECU ≠ interpreting the answer correctly. Each stage has its own level of evidence; none goes up without the matching evidence.",
    "Nenhuma combinação está ainda confirmada em hardware real com comunicação a uma centralina.":
        "No combination has yet been confirmed on real hardware communicating with an ECU.",
    "Compatibilidade de interfaces e protocolos":
        "Interface and protocol compatibility",
    "Fonte: rad/coverage.py · também em docs/COBERTURA.md":
        "Source: rad/coverage.py · also in docs/COVERAGE.md",
    "Módulos":
        "Modules",
    "Tipo":
        "Type",
    "Veículo":
        "Vehicle",
    "Origem":
        "Source",
    "Interface real":
        "Real interface",
    "Simulação":
        "Simulation",
    "Oficina":
        "Workshop",
    "Relatório":
        "Report",
    "Comparar com anterior":
        "Compare with previous",
    "Apagar":
        "Delete",
    "Abrir pasta":
        "Open folder",
    "Ainda não há diagnósticos guardados. Faça um Auto-Scan para começar.":
        "No saved diagnostics yet. Run an Auto-Scan to get started.",
    "Não foi possível abrir o registo: {e}":
        "Could not open the record: {e}",
    "Escolha um diagnóstico da lista.":
        "Choose a diagnostic from the list.",
    "<p><b>{v}</b>: visita de {v2}/{v3}/{v4} comparada com {v5}/{v6}/{v7}.<br><span style='color:{MUTED}'>Só entram os controladores lidos nas duas visitas.</span></p>":
        "<p><b>{v}</b>: visit of {v2}/{v3}/{v4} compared with {v5}/{v6}/{v7}.<br><span style='color:{MUTED}'>Only modules read in both visits are included.</span></p>",
    "Novas":
        "New",
    "Resolvidas":
        "Resolved",
    "Mantêm-se":
        "Still present",
    "Não foi possível comparar: {e}":
        "Could not compare: {e}",
    "Não há uma visita anterior com a mesma matrícula para comparar.":
        "There is no previous visit with the same licence plate to compare with.",
    "Comparar com a visita anterior":
        "Compare with the previous visit",
    "Apagar este diagnóstico do histórico?":
        "Delete this diagnostic from the history?",
    "  Iniciar Auto-Scan":
        "  Start Auto-Scan",
    "Escolher controlador":
        "Choose module",
    "CENTRO DE LIGAÇÃO":
        "CONNECTION CENTRE",
    "Nenhuma comunicação feita nesta sessão.":
        "No communication in this session.",
    "Diagnósticos hoje":
        "Diagnostics today",
    "Diagnósticos este mês":
        "Diagnostics this month",
    "Avarias encontradas este mês":
        "Faults found this month",
    "Veículos no histórico":
        "Vehicles in history",
    "Controladores VAG":
        "VAG modules",
    "Auto-Scan com mapa do veículo":
        "Auto-Scan with vehicle map",
    "Ler todos os controladores VAG e ver no carro onde estão as avarias.":
        "Read every VAG module and see on the car where the faults are.",
    "PDF com o logo da oficina, as avarias e as causas prováveis.":
        "PDF with the workshop logo, the faults and the probable causes.",
    "Veículo em diagnóstico":
        "Vehicle being diagnosed",
    "Estes dados aparecem no relatório para o cliente.":
        "This data appears in the customer report.",
    "Últimos veículos":
        "Latest vehicles",
    "Ver histórico":
        "View history",
    "Os diagnósticos guardados aparecem aqui.":
        "Saved diagnostics appear here.",
    "Sem carro por perto? Experimente todas as funções com centralinas simuladas (motor 1.9 TDI, ABS e painel).":
        "No car nearby? Try every function with simulated ECUs (1.9 TDI engine, ABS and instrument cluster).",
    "Veículo sem matrícula":
        "Vehicle without licence plate",
    "nenhum controlador lido":
        "no module read",
    "sem avarias nos lidos":
        "no faults in the modules read",
    "{faults} avaria(s)":
        "{faults} fault(s)",
    "   ·   simulação":
        "   ·   simulation",
    "Fechar controlador":
        "Close module",
    "Informação":
        "Identification",
    "Medição":
        "Measuring",
    "Ajustes básicos":
        "Basic settings",
    "Adaptação":
        "Adaptation",
    "Codificação":
        "Coding",
    "Saídas":
        "Outputs",
    "Testes TDI":
        "TDI tests",
    "Alterações":
        "Changes",
    "Componente":
        "Component",
    "Nº de peça VAG":
        "VAG part number",
    "Módulo":
        "Module",
    "Protocolo":
        "Protocol",
    "Info extra":
        "Extra info",
    "Velocidade":
        "Baud rate",
    "Dados brutos":
        "Raw data",
    "Valores de medição":
        "Measuring values",
    "Copiar informação":
        "Copy identification",
    "Funções rápidas":
        "Quick functions",
    "Painéis de instrumentos do tipo Golf IV / Bora / Passat B5 / Octavia I: a revisão é reposta escrevendo 0 no canal de adaptação 02.":
        "Golf IV / Bora / Passat B5 / Octavia I type instrument clusters: the service reminder is reset by writing 0 to adaptation channel 02.",
    "Repor indicador de revisão":
        "Reset service reminder",
    "Repor o indicador de revisão (canal 02 = 0)?\nUse só em painéis compatíveis. O valor só é gravado se o painel aceitar o teste.":
        "Reset the service reminder (channel 02 = 0)?\nUse only on compatible clusters. The value is only saved if the cluster accepts the test.",
    "Apagar avarias":
        "Clear faults",
    "Código":
        "Code",
    "Descrição":
        "Description",
    "Tipo de avaria":
        "Fault type",
    "Gravidade":
        "Severity",
    "▶  Iniciar leitura":
        "▶  Start reading",
    "⏺  Gravar CSV":
        "⏺  Record CSV",
    "Grupo A":
        "Group A",
    "Grupo B":
        "Group B",
    "Grupo C":
        "Group C",
    "Ajustes básicos: o controlador executa a rotina de adaptação do grupo seleccionado enquanto estiver ON (ex.: grupo 060 borboleta, 098 caixa…). Siga sempre o procedimento de oficina do motor.":
        "Basic settings: the module runs the adaptation routine of the selected group while it is ON (e.g. group 060 throttle, 098 gearbox…). Always follow the engine's workshop procedure.",
    "Ajuste básico  ON":
        "Basic setting  ON",
    "Canal ":
        "Channel ",
    "Canal":
        "Channel",
    "Ler":
        "Read",
    "Valor guardado":
        "Stored value",
    "Novo valor":
        "New value",
    "Testar":
        "Test",
    "Valor em teste":
        "Test value",
    "Código de oficina":
        "Workshop code",
    "Gravar":
        "Save",
    "Canal 00 = repor todas as adaptações (cuidado!). Alguns canais exigem Login antes.":
        "Channel 00 = reset all adaptations (careful!). Some channels need a Login first.",
    "Codificação actual":
        "Current coding",
    "Nova codificação (0–32767)":
        "New coding (0–32767)",
    "Codificar!":
        "Code it!",
    "Uma codificação errada pode desactivar funções ou acender avisos. Cada codificação gravada fica no separador Alterações, com o valor anterior, para poder voltar atrás.":
        "Wrong coding can disable functions or turn on warning lights. Every coding saved goes to the Changes tab, with the previous value, so you can go back.",
    "Código de login (5 dígitos)":
        "Login code (5 digits)",
    "Fazer login":
        "Log in",
    "Exemplos comuns: motor 12233 (cruise control em alguns EDC15), painel 13861 (algumas adaptações). Confirme sempre para o seu controlador.":
        "Common examples: engine 12233 (cruise control on some EDC15), instrument cluster 13861 (some adaptations). Always confirm it for your module.",
    "Activa os actuadores um a um (relés, electroválvulas…). Com o motor DESLIGADO e ignição ligada. Carregue em 'Seguinte' para avançar.":
        "Activates the actuators one by one (relays, solenoid valves…). With the engine OFF and the ignition on. Click 'Next' to move on.",
    "▶  Iniciar / Seguinte":
        "▶  Start / Next",
    "{part}   {component}   ·   {protocol} @ {baud} baud":
        "{part}   {component}   ·   {protocol} @ {baud} baud",
    "{baud} baud":
        "{baud} baud",
    "Código de oficina {wsc:05d}":
        "Workshop code {wsc:05d}",
    "Código de oficina —":
        "Workshop code —",
    "Campo {index}":
        "Field {index}",
    "Testes rápidos ao motor 1.9 TDI. Escolha o teste, siga as instruções e veja o resultado no fim. As referências são valores habituais de oficina.":
        "Quick tests for the 1.9 TDI engine. Choose the test, follow the instructions and see the result at the end. The references are usual workshop values.",
    "Escolha um teste":
        "Choose a test",
    "▶  Iniciar teste":
        "▶  Start test",
    "{title}  ·  grupo {group:03d}":
        "{title}  ·  group {group:03d}",
    "■  Parar e ver resultado":
        "■  Stop and see result",
    "{elapsed:.0f} / {duration} s   ·   {v} leituras":
        "{elapsed:.0f} / {duration} s   ·   {v} readings",
    "{elapsed:.0f} s   ·   {n} leituras":
        "{elapsed:.0f} s   ·   {n} readings",
    "✔  Nenhuma avaria":
        "✔  No faults",
    "⚠  {v} avaria(s)":
        "⚠  {v} fault(s)",
    "Permanente":
        "Permanent",
    "Apagar a memória de avarias deste controlador?":
        "Clear this module's fault memory?",
    "{v} avaria(s) encontrada(s):":
        "{v} fault(s) found:",
    "Nº de peça: {part}":
        "Part number: {part}",
    "Componente: {component}":
        "Component: {component}",
    "Codificação: {v}":
        "Coding: {v}",
    "WSC: {wsc:05d}":
        "WSC: {wsc:05d}",
    "Protocolo: {protocol} @ {baud} baud":
        "Protocol: {protocol} @ {baud} baud",
    "Active pelo menos um grupo.":
        "Enable at least one group.",
    "■  Parar leitura":
        "■  Stop reading",
    "controlador":
        "module",
    "Ligar o ajuste básico do grupo {g:03d} em {name}?\n\nO controlador executa a rotina de adaptação deste grupo enquanto estiver ON (pode mexer em actuadores). Siga o procedimento de oficina do motor.":
        "Turn on basic setting for group {g:03d} on {name}?\n\nThe module runs this group's adaptation routine while it is ON (it may move actuators). Follow the engine's workshop procedure.",
    "Ajuste básico  OFF":
        "Basic setting  OFF",
    "{v:.1f} leituras/s":
        "{v:.1f} readings/s",
    "RAD_{address:02X}_{v:%Y%m%d_%H%M%S}.csv":
        "RAD_{address:02X}_{v:%Y%m%d_%H%M%S}.csv",
    "Gravar valores em CSV":
        "Record values to CSV",
    "CSV (*.csv)":
        "CSV (*.csv)",
    "Não foi possível criar o ficheiro:\n{e}":
        "Could not create the file:\n{e}",
    "Hora":
        "Time",
    "⏹  Parar gravação":
        "⏹  Stop recording",
    "Codificações e adaptações gravadas neste controlador (identificado pelo endereço e pelo nº de peça), com o valor que lá estava antes. Para voltar atrás, escolha uma linha: o valor anterior é preparado no separador certo e só é gravado depois de o confirmar.":
        "Codings and adaptations written to this module (identified by its address and part number), with the value it had before. To go back, choose a row: the previous value is prepared in the right tab and is only written after you confirm it.",
    "Codificação original":
        "Original coding",
    "Preparar codificação original":
        "Prepare original coding",
    "Alteração":
        "Change",
    "Antes":
        "Before",
    "Data":
        "Date",
    "Depois":
        "After",
    "Preparar valor anterior":
        "Prepare previous value",
    "Actualizar":
        "Refresh",
    "Não foi possível ler o registo de alterações: {e}":
        "Could not read the change log: {e}",
    "{v} alteração(ões)":
        "{v} change(s)",
    "Sem alterações registadas":
        "No changes recorded",
    "Adaptação — canal {channel:02d}":
        "Adaptation — channel {channel:02d}",
    "por confirmar":
        "unconfirmed",
    "Gravar o valor {val} no canal {ch:02d} de {name}?":
        "Save the value {val} to channel {ch:02d} of {name}?",
    "ATENÇÃO: o canal 00 repõe TODAS as adaptações de {name} nos valores de fábrica.\n\nDepois pode ser preciso refazer ajustes básicos (ex.: borboleta, caixa). Continuar?":
        "WARNING: channel 00 resets ALL adaptations of {name} to factory values.\n\nBasic settings may need to be redone afterwards (e.g. throttle, gearbox). Continue?",
    "Codificação inválida (0 a 32767).":
        "Invalid coding (0 to 32767).",
    "Código de login inválido (00000 a 65535).":
        "Invalid login code (00000 to 65535).",
    "Iniciar o teste de saídas em {name}?\n\nOs actuadores vão ser activados um a um (relés, electroválvulas…). Motor DESLIGADO, ignição ligada e ninguém a mexer no compartimento do motor.":
        "Start the output test on {name}?\n\nThe actuators will be activated one by one (relays, solenoid valves…). Engine OFF, ignition on and nobody working in the engine bay.",
    "Fim do teste":
        "End of test",
    "Carregue em 'Iniciar' para recomeçar.":
        "Click 'Start' to begin again.",
    "— fim —":
        "— end —",
    "Seleccionar controlador":
        "Select module",
    "Endereço (ex.: 01)":
        "Address (e.g. 01)",
    "Ligar!":
        "Connect!",
    "Filtrar (ex.: motor, abs, 17)":
        "Filter (e.g. engine, abs, 17)",
    "erro":
        "error",
    "O endereço tem de estar entre 01 e 7F.":
        "The address must be between 01 and 7F.",
    "SIMULAÇÃO":
        "SIMULATION",
    "Sem ligação ao veículo":
        "Not connected to the vehicle",
    "Ligar ao veículo":
        "Connect to vehicle",
    "Desligar":
        "Disconnect",
    "PASSOS DA LIGAÇÃO":
        "CONNECTION STEPS",
    "Dados em tempo real":
        "Live data",
    "Prontidão":
        "Readiness",
    "Imagem congelada":
        "Freeze frame",
    "Apagar avarias…":
        "Clear faults…",
    "Centralina":
        "ECU",
    "Seleccione uma avaria para ver a categoria, a origem da descrição e o que verificar.":
        "Select a fault to see its category, where the description comes from and what to check.",
    "Parâmetros suportados (até {MAX_LIVE})":
        "Supported parameters (up to {MAX_LIVE})",
    "Iniciar leitura":
        "Start reading",
    "Máx.":
        "Max.",
    "Mín.":
        "Min.",
    "Parâmetro":
        "Parameter",
    "Unidade":
        "Unit",
    "Valor":
        "Value",
    "Seleccione um parâmetro na tabela para ver o gráfico.":
        "Select a parameter in the table to see the chart.",
    "Os monitores de prontidão dizem se os auto-testes de emissões já correram desde o último apagar de avarias (importante para a inspecção).":
        "Readiness monitors show whether the emission self-tests have run since faults were last cleared (important for the roadworthiness test).",
    "Monitor":
        "Monitor",
    "Calibração":
        "Calibration",
    "Parâmetros":
        "Parameters",
    "Pedido UDS":
        "UDS request",
    "Aguarde — ainda a comunicar com o veículo…":
        "Please wait — still communicating with the vehicle…",
    "Cancelar":
        "Cancel",
    "Seleccione uma centralina na tabela.":
        "Select an ECU in the table.",
    "No máximo {MAX_LIVE} parâmetros ao mesmo tempo (cada um é um pedido ao veículo).":
        "At most {MAX_LIVE} parameters at the same time (each one is a request to the vehicle).",
    "Marque pelo menos um parâmetro na lista.":
        "Tick at least one parameter in the list.",
    "Parar leitura":
        "Stop reading",
    "Ligado ao veículo":
        "Connected to the vehicle",
    "declarado pela centralina ":
        "declared by the ECU ",
    "não disponível":
        "not available",
    "ACESA":
        "ON",
    "{v} avaria(s) declarada(s) pelas centralinas":
        "{v} fault(s) declared by the ECUs",
    "não medida":
        "not measured",
    "PID {pid:02X} — {name}":
        "PID {pid:02X} — {name}",
    "A centralina não declarou parâmetros que o programa saiba interpretar.":
        "The ECU did not declare any parameters the program knows how to interpret.",
    "Carregue em Ler avarias.":
        "Click Read faults.",
    "contínuo":
        "continuous",
    "não contínuo":
        "non-continuous",
    "Sem descrição na base instalada — {category}":
        "No description in the installed database — {category}",
    "Nenhuma avaria nas centralinas que responderam (":
        "No faults in the ECUs that answered (",
    "pendentes":
        "pending",
    "permanentes":
        "permanent",
    "Não suportado pelo veículo: {kinds}.":
        "Not supported by the vehicle: {kinds}.",
    "Sem descrição na base instalada ({category})":
        "No description in the installed database ({category})",
    "depois de apagar":
        "after clearing",
    "Nenhuma imagem congelada guardada na centralina principal.":
        "No freeze frame stored in the main ECU.",
    "<p>Condições no momento em que a avaria <b>{dtc}</b> foi registada (centralina {ecu}):</p>":
        "<p>Conditions at the moment fault <b>{dtc}</b> was stored (ECU {ecu}):</p>",
    "(sem descrição)":
        "(no description)",
    "Ligação ao veículo perdida":
        "Connection to the vehicle lost",
    "Ligação fechada.":
        "Connection closed.",
    "Configuração":
        "Settings",
    "Automático (o adaptador procura)":
        "Automatic (the adapter searches)",
    "ISO 15765-4 CAN 11 bits 500k":
        "ISO 15765-4 CAN 11-bit 500k",
    "ISO 15765-4 CAN 11 bits 250k":
        "ISO 15765-4 CAN 11-bit 250k",
    "ISO 15765-4 CAN 29 bits 500k":
        "ISO 15765-4 CAN 29-bit 500k",
    "ISO 14230-4 KWP rápido":
        "ISO 14230-4 KWP fast",
    "ISO 15765-4 CAN 29 bits 250k":
        "ISO 15765-4 CAN 29-bit 250k",
    "ISO 14230-4 KWP 5 baud":
        "ISO 14230-4 KWP 5-baud",
    "ISO 9141-2":
        "ISO 9141-2",
    "SAE J1850 VPW":
        "SAE J1850 VPW",
    "SAE J1850 PWM":
        "SAE J1850 PWM",
    "Protocolo OBD":
        "OBD protocol",
    "Automática":
        "Automatic",
    "Automático":
        "Automatic",
    "Com eco (KKL normal)":
        "With echo (standard KKL)",
    "Sem eco":
        "No echo",
    "Registo detalhado: todos os blocos e bytes (para enviar quando houver problemas)":
        "Detailed log: every block and byte (to send when there are problems)",
    "Debug":
        "Debug",
    "Cabo":
        "Cable",
    "Ler modo do cabo":
        "Read cable mode",
    "Repor modo inteligente":
        "Restore smart mode",
    "Cabo HEX":
        "HEX cable",
    "Dados da oficina":
        "Workshop details",
    "Aparecem no cabeçalho do relatório para o cliente.":
        "Shown in the header of the customer report.",
    "Morada":
        "Address",
    "Nome da oficina":
        "Workshop name",
    "Telefone":
        "Phone",
    "Email":
        "Email",
    "NIF":
        "VAT number",
    "Escolher imagem…":
        "Choose image…",
    "Remover":
        "Remove",
    "O logótipo aparece no relatório para o cliente e na barra lateral do programa.":
        "The logo appears in the customer report and in the program's sidebar.",
    "Licença":
        "Licence",
    "ID deste PC":
        "This PC's ID",
    "Cole aqui a chave de licença (começa por RAD1-)":
        "Paste the licence key here (starts with RAD1-)",
    "Chave":
        "Key",
    "Activar licença":
        "Activate licence",
    "Remover licença":
        "Remove licence",
    "Para comprar ou renovar, envie o ID deste PC ao fornecedor. A activação não precisa de internet. Sem licença o programa lê tudo, mas não escreve em carros reais (codificação, adaptação, ajustes básicos, apagar avarias, teste de saídas).":
        "To buy or renew, send this PC's ID to your supplier. Activation does not need internet. Without a licence the program reads everything but does not write to real cars (coding, adaptation, basic settings, clearing faults, output tests).",
    "Actualizações":
        "Updates",
    "Procurar agora":
        "Check now",
    "Versão instalada: {VERSION}":
        "Installed version: {VERSION}",
    "Versão":
        "Version",
    "Ecrã":
        "Display",
    "Grande (115%)":
        "Large (115%)",
    "Muito grande (130%)":
        "Extra large (130%)",
    "Normal (100%)":
        "Normal (100%)",
    "Oficina — ver ao longe (150%)":
        "Workshop — view from a distance (150%)",
    "Tamanho da interface":
        "Interface size",
    "Idioma":
        "Language",
    "O tamanho aumenta letras, botões e mostradores para se lerem a partir do carro. O tamanho e o idioma aplicam-se quando o programa voltar a abrir.":
        "The size option enlarges text, buttons and gauges so they can be read from the car. Size and language take effect the next time the program opens.",
    "Guardar":
        "Save",
    "Pacote de suporte":
        "Support package",
    "Abrir pasta de registos":
        "Open logs folder",
    "Sem logótipo":
        "No logo",
    "Logótipo da oficina":
        "Workshop logo",
    "Imagens (*.png *.jpg *.jpeg *.bmp *.webp)":
        "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
    "Não foi possível abrir essa imagem.":
        "Could not open that image.",
    "Não foi possível guardar o logótipo.":
        "Could not save the logo.",
    "O tamanho e o idioma da interface aplicam-se quando voltar a abrir o programa.":
        "Interface size and language take effect the next time you open the program.",
    "Erro: {res}":
        "Error: {res}",
    "Versão instalada: {VERSION}. {text}":
        "Installed version: {VERSION}. {text}",
    "Não foi possível procurar actualizações.\n\n{text}":
        "Could not check for updates.\n\n{text}",
    "Versão instalada: {VERSION}. Nova versão disponível: {version}.":
        "Installed version: {VERSION}. New version available: {version}.",
    "Versão instalada: {VERSION}. É a versão mais recente.":
        "Installed version: {VERSION}. This is the latest version.",
    "Tem a versão mais recente ({VERSION}).":
        "You have the latest version ({VERSION}).",
    "Cole primeiro a chave de licença.":
        "Paste the licence key first.",
    "Não foi possível guardar a licença:\n{e}":
        "Could not save the licence:\n{e}",
    "Licença activada para {workshop}.":
        "Licence activated for {workshop}.",
    "Remover a licença deste PC? O programa volta ao modo demonstração.":
        "Remove the licence from this PC? The program goes back to demo mode.",
    "A procurar…":
        "Searching…",
    "Não foi possível procurar o cabo:\n{res}":
        "Could not search for the cable:\n{res}",
    "<br><a href='{driver_url}'>Página oficial do driver</a>":
        "<br><a href='{driver_url}'>Official driver page</a>",
    "<p><b>Interfaces J2534 (PassThru) instaladas:</b></p><ul>":
        "<p><b>Installed J2534 (PassThru) interfaces:</b></p><ul>",
    "<li><b>{name}</b> — {vendor} ({view})<br>Protocolos: {v}<br><small>{dll}</small></li>":
        "<li><b>{name}</b> — {vendor} ({view})<br>Protocols: {v}<br><small>{dll}</small></li>",
    "<p>Nenhuma interface J2534 (PassThru) registada neste PC.</p>":
        "<p>No J2534 (PassThru) interface registered on this PC.</p>",
    "Abrir Gestor de Dispositivos":
        "Open Device Manager",
    "RootsAutoDoctor_suporte_{v:%Y%m%d_%H%M}.zip":
        "RootsAutoDoctor_support_{v:%Y%m%d_%H%M}.zip",
    "Guardar pacote de suporte":
        "Save support package",
    "Zip (*.zip)":
        "Zip (*.zip)",
    "Não foi possível criar o pacote:\n{e}":
        "Could not create the package:\n{e}",
    "Procurar páginas, controladores, acções ou avarias (ex.: 00532, turbo)…":
        "Search pages, modules, actions or faults (e.g. 00532, turbo)…",
    "Duplo clique para abrir o gráfico":
        "Double-click to open the chart",
    "fórmula {formula}   a={a}   b={b}\nDuplo clique para abrir o gráfico":
        "formula {formula}   a={a}   b={b}\nDouble-click to open the chart",
    "Campo {n}":
        "Field {n}",
    "{unit}   ·   máx {v}":
        "{unit}   ·   max {v}",
    "{n} avaria{v}":
        "{n} fault{v}",
    "Sem comunicação":
        "No communication",
    "Clique para ligar a este controlador":
        "Click to connect to this module",
    "Abrir  →":
        "Open  →",
    "À espera de dados — inicie a leitura":
        "Waiting for data — start reading",
    "Grupo {group:03d} · campo {index} — {title}":
        "Group {group:03d} · field {index} — {title}",
    "Limpar":
        "Clear",
    "Fechar":
        "Close",
    "Valor actual: {value} {unit} (não numérico)":
        "Current value: {value} {unit} (not numeric)",
    "Actual {value} {u}     mín {v}     máx {v2}     média {v3}":
        "Current {value} {u}     min {v}     max {v2}     average {v3}",
    "SAÚDE":
        "HEALTH",
    "sem comunicação":
        "no communication",
    "sem avarias":
        "no faults",
    "{a:02X} · {v}\n{st}\nClique para ligar":
        "{a:02X} · {v}\n{st}\nClick to connect",
    "Avarias":
        "Faults",
    "Sem dados":
        "No data",
    "Bom estado":
        "Good condition",
    "Requer atenção":
        "Needs attention",
    "Intervenção recomendada":
        "Repair recommended",
    "Descrição não disponível na base de dados":
        "Description not available in the database",
    "Tipo {n:02d}":
        "Type {n:02d}",
    "(fórm. {formula})":
        "(form. {formula})",
    "Erro: {e}":
        "Error: {e}",
    "Ligação perdida: {reason}":
        "Connection lost: {reason}",
    "Ligação à centralina perdida: {reason}":
        "Connection to the ECU lost: {reason}",
    "Interface fechada depois de um erro; será reaberta no próximo comando.":
        "Interface closed after an error; it will be reopened on the next command.",
    "Escolha a porta do cabo nas Opções":
        "Choose the cable port in Options",
    "Interface {port} aberta":
        "Interface {port} open",
    "Cabo HEX: ":
        "HEX cable: ",
    "Cabo HEX: linha K vista pelo cabo — ":
        "HEX cable: K-line as seen by the cable — ",
    " (DTR {v}, RTS {v2} — guardado)":
        " (DTR {v}, RTS {v2} — saved)",
    "Eco da linha K OK":
        "K-line echo OK",
    "Erro interno: {e}":
        "Internal error: {e}",
    "Não há ligação ao controlador":
        "No connection to the module",
    "Aviso: a alteração foi feita mas não ficou no registo de alterações.":
        "Warning: the change was made but was not recorded in the change log.",
    "Interface alterada nas Opções.":
        "Interface changed in Options.",
    "Ligado a {address:02X} — {part} {component}":
        "Connected to {address:02X} — {part} {component}",
    "Controlador fechado. A interface continua aberta.":
        "Module closed. The interface stays open.",
    "Sem ligação.":
        "Not connected.",
    "A porta escolhida não é um cabo HEX (D2XX:… ou FTDI:0403:FA2x:…)":
        "The selected port is not a HEX cable (D2XX:… or FTDI:0403:FA2x:…)",
    "\n\nModo de arranque agora: {v}":
        "\n\nStart-up mode now: {v}",
    "Nenhuma porta escolhida. Use Detectar cabo.":
        "No port chosen. Use Detect cable.",
    "Porta do cabo":
        "Cable port",
    "Adaptador (microcontrolador do cabo HEX)":
        "Adapter (HEX cable microcontroller)",
    "Linha K vista pelo cabo":
        "K-line as seen by the cable",
    "KKL (linha K directa)":
        "KKL (direct K-line)",
    "Modo do cabo":
        "Cable mode",
    "Modo inteligente: a linha K é controlada pelo microcontrolador do cabo e o protocolo dele para falar com as centralinas ainda não está implementado no Roots Auto Doctor":
        "Smart mode: the K-line is controlled by the cable's microcontroller, and its protocol for talking to ECUs is not yet implemented in Roots Auto Doctor",
    "Eco da linha K":
        "K-line echo",
    "Ligação ao controlador {address:02X}":
        "Connection to module {address:02X}",
    "{protocol} a {baud} baud — {part} {component}":
        "{protocol} at {baud} baud — {part} {component}",
    "Leitura de avarias":
        "Fault reading",
    "{n} avaria(s)":
        "{n} fault(s)",
    "{e}. Confirme que a ignição está ligada; experimente outro endereço (ex.: 17).":
        "{e}. Make sure the ignition is on; try another address (e.g. 17).",
    "Apagar avarias {addr:02X}: {error}":
        "Clear faults {addr:02X}: {error}",
    "Ligação OBD perdida: {reason}":
        "OBD connection lost: {reason}",
    "Ligação ao veículo perdida: {reason}":
        "Connection to the vehicle lost: {reason}",
    "A porta {port} não aparece no computador: ligue o adaptador (ou emparelhe o Bluetooth) e carregue em Actualizar nas Opções.":
        "Port {port} does not appear on the computer: plug the adapter in (or pair the Bluetooth) and click Refresh in Options.",
    "OBD-II: ligado — {protocol}, {v} centralina(s)":
        "OBD-II: connected — {protocol}, {v} ECU(s)",
    ", VIN {vin}":
        ", VIN {vin}",
    "OBD-II: pedido de apagar avarias (modo 04) enviado por acção do utilizador":
        "OBD-II: request to clear faults (mode 04) sent by user action",
    "A centralina deixou de responder ({OBD_LIVE_MAX_SILENT} leituras seguidas sem resposta): ignição desligada ou cabo solto?":
        "The ECU stopped answering ({OBD_LIVE_MAX_SILENT} readings in a row without an answer): ignition off or loose cable?",
    "(estado)":
        "(status)",
    "-":
        "-",
    "1º mapa":
        "1st map",
    "2º mapa":
        "2nd map",
    "A leitura de centralinas passa pelo protocolo próprio do microcontrolador; a captura do arranque do VCDS mostra uma troca aparentemente autenticada/cifrada. Não se replica nem contorna: este cabo não lê centralinas no Roots Auto Doctor. Modo KKL do firmware testado no carro: sem linha K directa.":
        "Reading ECUs goes through the microcontroller's own protocol; the capture of VCDS starting up shows an exchange that looks authenticated/encrypted. It is neither replicated nor bypassed: this cable does not read ECUs in Roots Auto Doctor. Firmware KKL mode tested on the car: no direct K-line.",
    "ABS / travões":
        "ABS / brakes",
    "Accionamento da borboleta (G186) — avaria eléctrica":
        "Throttle actuator (G186) — electrical fault",
    "Acesso e arranque (Kessy)":
        "Access and start (Kessy)",
    "Actuador da borboleta comandado":
        "Commanded throttle actuator",
    "Adaptador CAN cru (tramas CAN; ex.: SLCAN, SocketCAN)":
        "Raw CAN adapter (CAN frames; e.g. SLCAN, SocketCAN)",
    "Adaptador ELM327 (USB / Bluetooth, porta COM)":
        "ELM327 adapter (USB / Bluetooth, COM port)",
    "Adaptação da mistura":
        "Mixture adaptation",
    "Adaptação de chaves / motor exige PIN (login) e o procedimento do fabricante":
        "Key / engine adaptation needs a PIN (login) and the manufacturer's procedure",
    "Admissão":
        "Intake",
    "Ajuda de estacionamento":
        "Parking aid",
    "Ajuste básico":
        "Basic setting",
    "Ajuste básico do corpo de borboleta (grupo 060 ou 098 conforme o motor)":
        "Throttle body basic setting (group 060 or 098 depending on the engine)",
    "Ajuste básico não efectuado":
        "Basic setting not carried out",
    "Ajuste básico não efectuado: execute o ajuste básico do componente.":
        "Basic setting not carried out: run the component's basic setting.",
    "Ajuste básico: execute o ajuste básico do componente depois de resolver a causa.":
        "Basic setting: run the component's basic setting after fixing the cause.",
    "Ajuste da borboleta — avaria na adaptação":
        "Throttle adjustment — adaptation malfunction",
    "Ajuste de combustível (banco 1)":
        "Fuel trim (bank 1)",
    "Alimentação eléctrica":
        "Electrical supply",
    "Alta":
        "High",
    "Alternador/regulador com carga insuficiente":
        "Alternator/regulator charging insufficiently",
    "Amortecimento das rodas":
        "Wheel damping",
    "Andares de saída na unidade de comando":
        "Output stages in the control unit",
    "Anel/roda fónica partida, oxidada ou com dentes em falta":
        "Broken, rusty or tooth-missing tone ring/reluctor",
    "Anotar a codificação actual antes de mexer":
        "Note down the current coding before changing anything",
    "Apagar e voltar a ler; se regressar, unidade a reparar/substituir":
        "Clear and read again; if it comes back, the unit needs repair/replacement",
    "Apertar o sensor com o binário correcto (normalmente 20 Nm)":
        "Tighten the sensor to the correct torque (usually 20 Nm)",
    "Aquecimento auxiliar":
        "Auxiliary heater",
    "Aquecimento da sonda avariado":
        "Sensor heater faulty",
    "Aquecimento da sonda lambda":
        "Oxygen sensor heater",
    "Aquecimento da sonda lambda (banco 1, sensor 1) — circuito":
        "Oxygen sensor heater (bank 1, sensor 1) — circuit",
    "Aquecimento da sonda lambda (banco 1, sensor 2) — circuito":
        "Oxygen sensor heater (bank 1, sensor 2) — circuit",
    "Aquecimentos":
        "Warm-ups",
    "Aquecimentos desde que as avarias foram apagadas":
        "Warm-ups since faults were cleared",
    "Ar condicionado / Climatronic":
        "Air conditioning / Climatronic",
    "Ar secundário":
        "Secondary air",
    "Arranques com cabos de bateria ou bateria desligada recentemente":
        "Jump starts or battery recently disconnected",
    "Arrefecimento":
        "Cooling",
    "Atrelado":
        "Trailer",
    "Autocom / Delphi CDP+ (e clones)":
        "Autocom / Delphi CDP+ (and clones)",
    "Avanço":
        "Timing",
    "Avanço da bomba mal ajustado":
        "Pump timing incorrectly adjusted",
    "Avanço da ignição":
        "Ignition timing",
    "Avanço da ignição (cilindro 1)":
        "Ignition timing (cylinder 1)",
    "Avaria eléctrica no circuito":
        "Electrical fault in circuit",
    "Avaria interna":
        "Internal fault",
    "Avaria interna da unidade de comando":
        "Internal control unit fault",
    "Avaria mecânica":
        "Mechanical malfunction",
    "Avaria no ajuste básico":
        "Basic setting malfunction",
    "Avaria no sistema de refrigeração":
        "Cooling system malfunction",
    "Baixa":
        "Low",
    "Banco condutor":
        "Driver's seat",
    "Banco passageiro":
        "Passenger seat",
    "Barramento CAN de alta velocidade — comunicação":
        "High-speed CAN bus — communication",
    "Barramento de dados do grupo motopropulsor":
        "Powertrain data bus",
    "Barramento de dados — falta mensagem do painel de instrumentos":
        "Data bus — missing message from the instrument cluster",
    "Base genérica do Roots Auto Doctor — títulos resumidos dos códigos normalizados SAE J2012 / ISO 15031-6 (só códigos genéricos; confirmar sempre com a documentação do fabricante)":
        "Roots Auto Doctor generic database — summarised titles of the standardised SAE J2012 / ISO 15031-6 codes (generic codes only; always confirm with the manufacturer's documentation)",
    "Bateria":
        "Battery",
    "Bateria desligada ou componente substituído sem ajuste básico":
        "Battery disconnected or component replaced without basic setting",
    "Bateria fraca ou descarregada (tensão baixa no arranque)":
        "Weak or flat battery (low voltage while cranking)",
    "Bi-combustível GNC":
        "Bi-fuel CNG",
    "Bi-combustível GPL":
        "Bi-fuel LPG",
    "Bi-combustível eléctrico":
        "Bi-fuel electric",
    "Bi-combustível etanol":
        "Bi-fuel ethanol",
    "Bi-combustível gasolina":
        "Bi-fuel petrol",
    "Bi-combustível metanol":
        "Bi-fuel methanol",
    "Bi-combustível propano":
        "Bi-fuel propane",
    "Binário de referência do motor":
        "Engine reference torque",
    "Binário pedido":
        "Requested torque",
    "Binário pedido pelo condutor":
        "Driver-demanded torque",
    "Binário real":
        "Actual torque",
    "Binário real do motor":
        "Actual engine torque",
    "Binário ref.":
        "Ref. torque",
    "Bloqueado":
        "Blocked",
    "Bloqueado ou sem tensão":
        "Blocked or no voltage",
    "Bloqueado ou sem tensão: verifique a alimentação do componente e se está mecanicamente preso.":
        "Blocked or no voltage: check the component's supply and whether it is mechanically stuck.",
    "Bobina de leitura (D2) no canhão de ignição avariada":
        "Faulty reader coil (D2) on the ignition lock",
    "Bobina de leitura do imobilizador (D2)":
        "Immobiliser reader coil (D2)",
    "Bobina do injector em curto ou interrompida":
        "Injector coil shorted or open",
    "Bomba de gasóleo":
        "Diesel pump",
    "Bomba de retorno ABS (V39)":
        "ABS return pump (V39)",
    "Bomba do ar secundário (V101)":
        "Secondary air pump (V101)",
    "Bomba hidráulica ABS (V64)":
        "ABS hydraulic pump (V64)",
    "Bomba hidráulica sem alimentação (fusível/relé)":
        "Hydraulic pump without supply (fuse/relay)",
    "Borboleta":
        "Throttle",
    "Borboleta B":
        "Throttle B",
    "Borboleta cmd":
        "Throttle cmd",
    "Borboleta rel.":
        "Throttle rel.",
    "Buzina do alarme (H12)":
        "Alarm horn (H12)",
    "Bóia do depósito com o potenciómetro gasto":
        "Fuel tank float with a worn potentiometer",
    "Cablagem":
        "Wiring",
    "Cablagem da válvula":
        "Valve wiring",
    "Cablagem do barramento (CAN ou linha K) danificada ou com humidade":
        "Bus wiring (CAN or K-line) damaged or damp",
    "Cablagem do sensor":
        "Sensor wiring",
    "Cablagem do sensor danificada (zona quente)":
        "Sensor wiring damaged (hot area)",
    "Cablagem do sensor danificada junto à roda (zona de movimento)":
        "Sensor wiring damaged near the wheel (moving area)",
    "Cabo KKL 409.1 (FTDI / CH340, porta COM)":
        "KKL 409.1 cable (FTDI / CH340, COM port)",
    "Caixa automática":
        "Automatic gearbox",
    "Caixa de velocidades":
        "Gearbox",
    "Carga":
        "Load",
    "Carga abs.":
        "Abs. load",
    "Carga absoluta":
        "Absolute load",
    "Carga calculada do motor":
        "Calculated engine load",
    "Carga do motor":
        "Engine load",
    "Carroçaria":
        "Body",
    "Catalisador":
        "Catalyst",
    "Catalisador (banco 1) — eficiência abaixo do limite":
        "Catalyst (bank 1) — efficiency below threshold",
    "Catalisador (banco 2) — eficiência abaixo do limite":
        "Catalyst (bank 2) — efficiency below threshold",
    "Catalisador NMHC":
        "NMHC catalyst",
    "Catalisador aquecido":
        "Heated catalyst",
    "Catalisador degradado":
        "Degraded catalytic converter",
    "Centralinas OBD, VIN, nome/calibração, luz de avaria e monitores de prontidão, avarias memorizadas/pendentes/permanentes, apagar (modo 04, com confirmação e releitura), imagem congelada, dados actuais só dos PIDs declarados pela centralina":
        "OBD ECUs, VIN, name/calibration, malfunction indicator and readiness monitors, stored/pending/permanent faults, clearing (mode 04, with confirmation and re-read), freeze frame, live data only for the PIDs declared by the ECU",
    "Chave 1":
        "Key 1",
    "Chave 2":
        "Key 2",
    "Chave a ser retirada sem rodar completamente":
        "Key removed without turning it all the way",
    "Chave não adaptada a este carro ou transponder danificado":
        "Key not adapted to this car or damaged transponder",
    "Chave — sinal demasiado baixo":
        "Key — signal too low",
    "Ciclo EGR (N18)":
        "EGR duty cycle (N18)",
    "Ciclo N108":
        "N108 duty cycle",
    "Ciclo N75":
        "N75 duty cycle",
    "Circuito aberto":
        "Open circuit",
    "Circuito aberto ou curto ao positivo":
        "Open circuit or short to plus",
    "Circuito aberto ou curto ao positivo: verifique a ficha e a cablagem do componente.":
        "Open circuit or short to plus: check the component's connector and wiring.",
    "Circuito aberto ou curto à massa":
        "Open circuit or short to ground",
    "Circuito aberto ou curto à massa: verifique a ficha e a cablagem do componente.":
        "Open circuit or short to ground: check the component's connector and wiring.",
    "Circuito aberto ou curto-circuito: verifique a ficha e a cablagem do componente.":
        "Open circuit or short circuit: check the component's connector and wiring.",
    "Circuito aberto/curto-circuito":
        "Open circuit/short circuit",
    "Circuito aberto: meça a continuidade entre a unidade de comando e o componente; veja terminais oxidados.":
        "Open circuit: measure continuity between the control unit and the component; look for corroded terminals.",
    "Circuito da electroválvula do turbo":
        "Turbo solenoid valve circuit",
    "Circuito da luz das velas de incandescência":
        "Glow plug warning light circuit",
    "Circuito da sonda lambda (banco 1, sensor 1)":
        "Oxygen sensor circuit (bank 1, sensor 1)",
    "Circuito da válvula EGR":
        "EGR valve circuit",
    "Circuito das velas de incandescência":
        "Glow plug circuit",
    "Circuito do injector cilindro 1":
        "Cylinder 1 injector circuit",
    "Circuito do injector cilindro 2":
        "Cylinder 2 injector circuit",
    "Circuito do injector cilindro 3":
        "Cylinder 3 injector circuit",
    "Circuito do injector cilindro 4":
        "Cylinder 4 injector circuit",
    "Circuito do medidor de massa de ar":
        "Air mass meter circuit",
    "Circuito do sensor da cambota":
        "Crankshaft sensor circuit",
    "Circuito do sensor da árvore de cames":
        "Camshaft sensor circuit",
    "Circuito do sensor de posição da borboleta/pedal":
        "Throttle/pedal position sensor circuit",
    "Circuito do sensor de pressão do colector (MAP)":
        "Manifold pressure (MAP) sensor circuit",
    "Circuito do sensor de pressão do turbo":
        "Boost pressure sensor circuit",
    "Circuito do sensor de temperatura do ar de admissão":
        "Intake air temperature sensor circuit",
    "Circuito do sensor de temperatura do líquido de refrigeração":
        "Coolant temperature sensor circuit",
    "Climatização":
        "Climate control",
    "Clone HEX-USB+CAN (FTDI 0403:FA24, driver RT-USB ou WinUSB)":
        "HEX-USB+CAN clone (FTDI 0403:FA24, RT-USB or WinUSB driver)",
    "Codificar a unidade de acordo com o equipamento do carro (separador Codificação)":
        "Code the unit to match the car's equipment (Coding tab)",
    "Codificação errada (unidade espera um módulo que o carro não tem)":
        "Wrong coding (the unit expects a module the car does not have)",
    "Codificação não corresponde ao equipamento do carro":
        "Coding does not match the car's equipment",
    "Com o motor frio, a temperatura do ar deve ser próxima da ambiente":
        "With a cold engine, the air temperature should be close to ambient",
    "Com o motor parado, a pressão deve ser igual à atmosférica (~1000 mbar)":
        "With the engine stopped, the pressure should equal atmospheric pressure (~1000 mbar)",
    "Comando de voz":
        "Voice control",
    "Combustível":
        "Fuel",
    "Combustível de baixa qualidade":
        "Poor-quality fuel",
    "Comparar a leitura com a temperatura real":
        "Compare the reading with the real temperature",
    "Comparar a temperatura no grupo 001/004 com a temperatura real do motor frio":
        "Compare the temperature in group 001/004 with the real temperature of the cold engine",
    "Comparar o sinal das sondas antes e depois do catalisador":
        "Compare the signal of the sensors before and after the catalytic converter",
    "Componentes":
        "Components",
    "Compressão baixa":
        "Low compression",
    "Comunicação com a ECU":
        "Communication with the ECU",
    "Comunicação entre unidades":
        "Communication between units",
    "Confirmado em hardware real":
        "Confirmed on real hardware",
    "Confirmar a codificação do gateway / painel":
        "Confirm the gateway / instrument cluster coding",
    "Confirmar a sincronização da distribuição":
        "Confirm the timing synchronisation",
    "Confirmar o equipamento e corrigir a codificação":
        "Confirm the equipment and correct the coding",
    "Conforto":
        "Comfort",
    "Consequência de outra avaria do ABS (sensor, bomba)":
        "Consequence of another ABS fault (sensor, pump)",
    "Consumo":
        "Consumption",
    "Consumo de combustível do motor":
        "Engine fuel consumption",
    "Contacto S do canhão de ignição gasto":
        "Worn S contact on the ignition lock",
    "Contacto S no canhão de ignição (D)":
        "S contact on the ignition lock (D)",
    "Contactos do porta-relés oxidados":
        "Corroded relay carrier contacts",
    "Controlador desconhecido":
        "Unknown module",
    "Controlo da borboleta — avaria":
        "Throttle control — malfunction",
    "Controlo de detonação cilindro 1":
        "Knock control cylinder 1",
    "Controlo do ralenti — sistema":
        "Idle control — system",
    "Corpo de borboleta sujo":
        "Dirty throttle body",
    "Correcção de mistura curta — banco 1":
        "Short-term fuel trim — bank 1",
    "Correcção de mistura curta — banco 2":
        "Short-term fuel trim — bank 2",
    "Correcção de mistura longa — banco 1":
        "Long-term fuel trim — bank 1",
    "Correcção de mistura longa — banco 2":
        "Long-term fuel trim — bank 2",
    "Correcção lambda":
        "Lambda correction",
    "Correcção lambda depois do catalisador — limite atingido":
        "Lambda correction after catalyst — limit reached",
    "Correia de distribuição saltou um dente":
        "Timing belt jumped a tooth",
    "Curto-circuito ao positivo":
        "Short to plus",
    "Curto-circuito ao positivo: procure um fio descarnado a tocar em +12 V ou humidade na ficha.":
        "Short to plus: look for a bare wire touching +12 V or moisture in the connector.",
    "Curto-circuito entre si":
        "Short to each other",
    "Curto-circuito à massa":
        "Short to ground",
    "Curto-circuito à massa: cablagem a tocar na carroçaria — verifique o isolamento ao longo do fio.":
        "Short to ground: wiring touching the body — check the insulation along the wire.",
    "Dados de colisão memorizados":
        "Crash data stored",
    "Data de fabrico da centralina":
        "ECU manufacturing date",
    "Desligar a ficha do medidor e comparar o comportamento do motor":
        "Unplug the meter's connector and compare how the engine behaves",
    "Desvio cilindro 1":
        "Cylinder 1 deviation",
    "Desvio cilindro 2":
        "Cylinder 2 deviation",
    "Desvio cilindro 3":
        "Cylinder 3 deviation",
    "Desvio cilindro 4":
        "Cylinder 4 deviation",
    "Desvio de regulação":
        "Control deviation",
    "Desvio de regulação: compare o valor pretendido com o real nos valores de medição.":
        "Control deviation: compare the specified value with the actual one in the measuring values.",
    "Detecção":
        "Detection",
    "Detonador airbag condutor (N95)":
        "Driver airbag igniter (N95)",
    "Detonador airbag lateral condutor (N199)":
        "Driver side airbag igniter (N199)",
    "Detonador airbag lateral passageiro (N200)":
        "Passenger side airbag igniter (N200)",
    "Detonador airbag passageiro (N131)":
        "Passenger airbag igniter (N131)",
    "Direcção":
        "Steering",
    "Direcção assistida":
        "Power steering",
    "Dist. c/ MIL":
        "Dist. w/ MIL",
    "Dist. desde apagar":
        "Dist. since clear",
    "Distância com a luz de avaria acesa":
        "Distance travelled with the malfunction indicator on",
    "Distância desde que as avarias foram apagadas":
        "Distance since faults were cleared",
    "DoIP (ISO 13400), SAE J1939, CAN-FD":
        "DoIP (ISO 13400), SAE J1939, CAN-FD",
    "Débito injectado":
        "Injected quantity",
    "Débito pedido":
        "Requested quantity",
    "EGR cmd":
        "EGR cmd",
    "EGR comandada":
        "Commanded EGR",
    "EMD":
        "EMD",
    "EMD+":
        "EMD+",
    "EOBD (Europa)":
        "EOBD (Europe)",
    "EOBD e OBD":
        "EOBD and OBD",
    "EOBD e OBD-II":
        "EOBD and OBD-II",
    "EOBD, OBD e OBD-II":
        "EOBD, OBD and OBD-II",
    "Eficiência do catalisador abaixo do limite":
        "Catalyst efficiency below threshold",
    "Electroválvula N18 avariada":
        "Faulty N18 solenoid valve",
    "Electroválvula N75 avariada ou com membrana rota":
        "Faulty N75 solenoid valve or torn diaphragm",
    "Electroválvula de limitação da pressão avariada":
        "Faulty boost pressure limiting solenoid valve",
    "Electroválvula de limitação da pressão do turbo":
        "Boost pressure limiting solenoid valve",
    "Electroválvula de regulação da pressão do turbo (N75)":
        "Boost pressure control solenoid valve (N75)",
    "Electrónica central":
        "Central electronics",
    "Electrónica coluna direcção":
        "Steering column electronics",
    "Electrónica do motor":
        "Engine electronics",
    "Electrónica do motor 2":
        "Engine electronics 2",
    "Eléctrico":
        "Electric",
    "Em estrada e em segurança: engrene a 3ª, deixe cair a ~1500 rpm e acelere a fundo até ~3500 rpm. Depois carregue em Parar.":
        "On the road and safely: engage 3rd gear, let the revs drop to ~1500 rpm and accelerate fully to ~3500 rpm. Then click Stop.",
    "Emissões":
        "Emissions",
    "Entrada aberta":
        "Open input",
    "Entrada de ar falso":
        "Unmetered air",
    "Entrada de ar falso na admissão":
        "Unmetered air in the intake",
    "Equilíbrio dos injectores":
        "Injector balance",
    "Erro EGR":
        "EGR error",
    "Erro da EGR":
        "EGR error",
    "Erro de comunicação":
        "Communication error",
    "Erro de memória da unidade de comando":
        "Control unit memory error",
    "Esta avaria não se apaga":
        "This fault cannot be cleared",
    "Estado de funcionamento":
        "Operating state",
    "Estado de interruptor indefinido":
        "Undefined switch state",
    "Estado do ajuste básico":
        "Basic setting state",
    "Etanol":
        "Ethanol",
    "Executar o ajuste básico (separador Ajustes básicos, grupo indicado no manual)":
        "Run the basic setting (Basic settings tab, group given in the manual)",
    "Experimentar a chave suplente":
        "Try the spare key",
    "FRIO":
        "COLD",
    "Falha de combustão no cilindro 1":
        "Misfire on cylinder 1",
    "Falha de combustão no cilindro 2":
        "Misfire on cylinder 2",
    "Falha de combustão no cilindro 3":
        "Misfire on cylinder 3",
    "Falha de combustão no cilindro 4":
        "Misfire on cylinder 4",
    "Falha de combustão no cilindro 5":
        "Misfire on cylinder 5",
    "Falha de combustão no cilindro 6":
        "Misfire on cylinder 6",
    "Falha de ignição cilindro 1":
        "Cylinder 1 misfire",
    "Falha de ignição cilindro 2":
        "Cylinder 2 misfire",
    "Falha de ignição cilindro 3":
        "Cylinder 3 misfire",
    "Falha de ignição cilindro 4":
        "Cylinder 4 misfire",
    "Falhas de combustão":
        "Misfires",
    "Falhas de combustão aleatórias / em vários cilindros":
        "Random / multiple cylinder misfire",
    "Falhas de ignição aleatórias":
        "Random misfires",
    "Falta de ajuste básico depois de limpeza ou desmontagem":
        "Missing basic setting after cleaning or removal",
    "Falta o driver de um adaptador CAN concreto; o transporte está testado com um barramento simulado.":
        "The driver for a specific CAN adapter is missing; the transport is tested with a simulated bus.",
    "Faróis xénon / regulação":
        "Xenon headlights / levelling",
    "Fecho centralizado":
        "Central locking",
    "Ficha da N75 oxidada / cablagem cortada":
        "N75 connector corroded / wiring cut",
    "Ficha da bomba injectora com fuga de gasóleo":
        "Injection pump connector leaking diesel",
    "Ficha da bomba/sensor no depósito":
        "Pump/sensor connector in the tank",
    "Ficha do airbag/pré-tensor mal encaixada (muito comum debaixo dos bancos)":
        "Airbag/pretensioner connector not seated properly (very common under the seats)",
    "Ficha do pedal com mau contacto":
        "Pedal connector with poor contact",
    "Ficha do sensor desligada ou oxidada":
        "Sensor connector unplugged or corroded",
    "Ficha do sensor oxidada":
        "Corroded sensor connector",
    "Ficha ou cablagem do injector com mau contacto/oxidação":
        "Injector connector or wiring with poor contact/corrosion",
    "Ficha oxidada":
        "Corroded connector",
    "Ficheiro de descrição ODX":
        "ODX description file",
    "Filtro de ar muito sujo":
        "Very dirty air filter",
    "Filtro de partículas":
        "Particulate filter",
    "Filtro de partículas (banco 1) — eficiência abaixo do limite":
        "Particulate filter (bank 1) — efficiency below threshold",
    "Filtro de partículas — acumulação de fuligem":
        "Particulate filter — soot build-up",
    "Firmware fechado da Ross-Tech":
        "Ross-Tech closed firmware",
    "Firmware próprio":
        "Proprietary firmware",
    "Fita espiral do volante (contacto rotativo) partida":
        "Broken steering wheel clock spring (rotary contact)",
    "Fluxo EGR":
        "EGR flow",
    "Fluxo EGR excessivo":
        "Excessive EGR flow",
    "Fluxo EGR insuficiente":
        "Insufficient EGR flow",
    "Fluxo EGR — desvio":
        "EGR flow — deviation",
    "Folga excessiva no rolamento da roda":
        "Excessive play in the wheel bearing",
    "Folga/distância ao volante do motor incorrecta":
        "Incorrect gap/distance to the flywheel",
    "Fornecedor do sistema":
        "System supplier",
    "Fuga na admissão depois do medidor":
        "Intake leak after the meter",
    "Fuga no circuito de pressão (tubos, intercooler)":
        "Leak in the boost circuit (hoses, intercooler)",
    "Fuga no escape":
        "Exhaust leak",
    "Fuga no escape antes da sonda":
        "Exhaust leak before the sensor",
    "Fuga no sistema de admissão de ar":
        "Air intake system leak",
    "Fuga no sistema de combustível detectada (fuga grande)":
        "Fuel system leak detected (large leak)",
    "Fugas no circuito do turbo":
        "Leaks in the turbo circuit",
    "Funcionamento do ABS":
        "ABS operation",
    "Fusível/relé da bomba ABS":
        "ABS pump fuse/relay",
    "GNC":
        "CNG",
    "GPL":
        "LPG",
    "Gasolina":
        "Petrol",
    "Gasóleo":
        "Diesel",
    "Geometria do turbo presa":
        "Turbo geometry stuck",
    "Geometria variável do turbo presa (carvão)":
        "Variable turbo geometry stuck (carbon)",
    "Geral":
        "General",
    "Gravidade alta":
        "High severity",
    "Gravidade baixa":
        "Low severity",
    "Gravidade média":
        "Medium severity",
    "Gravidade não avaliada":
        "Severity not assessed",
    "Grupo 011":
        "Group 011",
    "Grupo 011 a acelerar em 3.ª":
        "Group 011 accelerating in 3rd gear",
    "Grupo 011: pressão pretendida vs real em aceleração":
        "Group 011: specified vs actual pressure while accelerating",
    "HD EOBD-I":
        "HD EOBD-I",
    "HD EOBD-I N":
        "HD EOBD-I N",
    "HD EOBD-II":
        "HD EOBD-II",
    "HD EOBD-II N":
        "HD EOBD-II N",
    "HD EOBD-IV":
        "HD EOBD-IV",
    "HD OBD":
        "HD OBD",
    "HD OBD-C":
        "HD OBD-C",
    "Híbrido eléctrico":
        "Hybrid electric",
    "Híbrido etanol":
        "Hybrid ethanol",
    "Híbrido gasolina":
        "Hybrid petrol",
    "Híbrido gasóleo":
        "Hybrid diesel",
    "IOBD I":
        "IOBD I",
    "IOBD II":
        "IOBD II",
    "ISO-TP (ISO 15765-2) + OBD-II / UDS":
        "ISO-TP (ISO 15765-2) + OBD-II / UDS",
    "ISO-TP completo (segmentação, Flow Control, STmin, pendente 0x78) e os mesmos serviços":
        "Full ISO-TP (segmentation, Flow Control, STmin, pending 0x78) and the same services",
    "Identificação normalizada (F187/F189/F18C/F190/F197…), avarias UDS com tipo de falha e estado; tratamento de 'resposta pendente' (NRC 78)":
        "Standard identification (F187/F189/F18C/F190/F197…), UDS faults with failure type and status; handling of 'response pending' (NRC 78)",
    "Identificação, avarias (ler/apagar com releitura), blocos de medição, ajuste básico, adaptação (com verificação), codificação (com verificação), login, teste de saídas":
        "Identification, faults (read/clear with re-read), measuring blocks, basic settings, adaptation (with verification), coding (with verification), login, output tests",
    "Ignição":
        "Ignition",
    "Ignição / canhão":
        "Ignition / lock",
    "Ignição DESLIGADA e bateria desligada antes de mexer em fichas de airbag":
        "Ignition OFF and battery disconnected before touching airbag connectors",
    "Iluminação":
        "Lighting",
    "Imobilizador":
        "Immobiliser",
    "Implementado, não validado":
        "Implemented, not validated",
    "Iniciação":
        "Initialisation",
    "Injector cilindro 1 (N30)":
        "Cylinder 1 injector (N30)",
    "Injector cilindro 2 (N31)":
        "Cylinder 2 injector (N31)",
    "Injector cilindro 3 (N32)":
        "Cylinder 3 injector (N32)",
    "Injector cilindro 4 (N33)":
        "Cylinder 4 injector (N33)",
    "Injector com débito fora de tolerância (desgaste)":
        "Injector delivery out of tolerance (wear)",
    "Injector do cilindro 1 — circuito":
        "Cylinder 1 injector — circuit",
    "Injector do cilindro 2 — circuito":
        "Cylinder 2 injector — circuit",
    "Injector do cilindro 3 — circuito":
        "Cylinder 3 injector — circuit",
    "Injector do cilindro 4 — circuito":
        "Cylinder 4 injector — circuit",
    "Injector do cilindro 5 — circuito":
        "Cylinder 5 injector — circuit",
    "Injector do cilindro 6 — circuito":
        "Cylinder 6 injector — circuit",
    "Injectores":
        "Injectors",
    "Injectores sujos":
        "Dirty injectors",
    "Injecção":
        "Injection",
    "Injecção (bomba VE)":
        "Injection (VE pump)",
    "Inspeccionar a ficha da bomba (gasóleo dentro da ficha)":
        "Inspect the pump connector (diesel inside the connector)",
    "Inspeccionar a roda fónica com a roda levantada, a rodar à mão":
        "Inspect the tone ring with the wheel raised, turning it by hand",
    "Inspecção completa do sistema de retenção (airbags, pré-tensores, unidade J234)":
        "Full inspection of the restraint system (airbags, pretensioners, J234 unit)",
    "Interface / protocolo":
        "Interface / protocol",
    "Interface J2534 04.04 (PassThru)":
        "J2534 04.04 interface (PassThru)",
    "Interface de diagnóstico do barramento (J533)":
        "Data bus diagnostic interface (J533)",
    "Interpretação":
        "Interpretation",
    "Interpretação das linhas com cabeçalho e checksum testada com linhas sintéticas; o simulador só imita CAN. Centralinas VAG antigas que só falam KW1281 não respondem por OBD-II.":
        "Interpretation of lines with header and checksum tested with synthetic lines; the simulator only imitates CAN. Older VAG ECUs that only speak KW1281 do not answer over OBD-II.",
    "Interruptor de ralenti (F60)":
        "Idle switch (F60)",
    "Início da injecção":
        "Start of injection",
    "Início de injecção pretendido":
        "Specified start of injection",
    "Início de injecção real":
        "Actual start of injection",
    "Início injecção":
        "Injection start",
    "JOBD (Japão)":
        "JOBD (Japan)",
    "JOBD e EOBD":
        "JOBD and EOBD",
    "JOBD e OBD-II":
        "JOBD and OBD-II",
    "JOBD, EOBD e OBD-II":
        "JOBD, EOBD and OBD-II",
    "KOBD":
        "KOBD",
    "KW1281 (linha K, init 5 baud) — VAG até ~2005":
        "KW1281 (K-line, 5-baud init) — VAG up to ~2005",
    "KWP2000 / ISO 14230 (linha K) — VAG":
        "KWP2000 / ISO 14230 (K-line) — VAG",
    "KWP2000 / ISO 14230 com init 5 baud":
        "KWP2000 / ISO 14230 with 5-baud init",
    "Lambda cmd":
        "Lambda cmd",
    "Ligado à centralina":
        "Connected to the ECU",
    "Ligar a essa unidade com o programa: se não responder, o problema está nela ou na cablagem":
        "Connect to that unit with the program: if it does not answer, the problem is in the unit or its wiring",
    "Ligação de comunicação série":
        "Serial communication link",
    "Ligação eléctrica motor-caixa":
        "Engine-gearbox electrical connection",
    "Ligação eléctrica motor-caixa 2":
        "Engine-gearbox electrical connection 2",
    "Limite de adaptação (adit.) excedido":
        "Adaptation limit (add.) exceeded",
    "Limite de adaptação (adit.) não atingido":
        "Adaptation limit (add.) not reached",
    "Limite de adaptação (mult.) excedido":
        "Adaptation limit (mult.) exceeded",
    "Limite de adaptação (mult.) não atingido":
        "Adaptation limit (mult.) not reached",
    "Limite de adaptação excedido":
        "Adaptation limit exceeded",
    "Limite de adaptação excedido (2)":
        "Adaptation limit exceeded (2)",
    "Limite de adaptação não atingido":
        "Adaptation limit not reached",
    "Limite de adaptação: a unidade já compensou o máximo que podia — procure a causa mecânica.":
        "Adaptation limit: the unit has already compensated as much as it can — look for the mechanical cause.",
    "Limite de regulação excedido":
        "Control limit exceeded",
    "Limite de regulação excedido: o sistema não consegue chegar ao valor pretendido (fugas, componente preso).":
        "Control limit exceeded: the system cannot reach the specified value (leaks, stuck component).",
    "Limite de regulação não atingido":
        "Control limit not reached",
    "Limite de regulação não atingido: o sistema não consegue chegar ao valor pretendido.":
        "Control limit not reached: the system cannot reach the specified value.",
    "Limite inferior":
        "Lower limit",
    "Limite por massa de ar":
        "Air mass limit",
    "Limite por rotação":
        "Engine speed limit",
    "Limite superior":
        "Upper limit",
    "Limpar a válvula / corpo de borboleta":
        "Clean the valve / throttle body",
    "Limpar a válvula EGR":
        "Clean the EGR valve",
    "Limpar e apertar terminais da bateria e as massas motor-carroçaria":
        "Clean and tighten the battery terminals and the engine-to-body grounds",
    "Limpar o corpo de borboleta":
        "Clean the throttle body",
    "Luz de avaria do motor (K83)":
        "Engine malfunction indicator lamp (K83)",
    "Luz de aviso das velas (K29)":
        "Glow plug warning lamp (K29)",
    "Luz direita":
        "Right headlight",
    "Luz esquerda":
        "Left headlight",
    "Lâmpada/LED do painel ou cablagem até ao painel":
        "Instrument cluster bulb/LED or wiring to the cluster",
    "MAF":
        "MAF",
    "Massa da unidade ABS com mau contacto":
        "Poor ground contact on the ABS unit",
    "Massa de ar":
        "Air mass",
    "Massa de ar (MAF)":
        "Air mass (MAF)",
    "Massa de ar pretendida":
        "Specified air mass",
    "Massa de ar real":
        "Actual air mass",
    "Massa ou positivo da unidade de comando com mau contacto":
        "Poor ground or positive contact on the control unit",
    "Mau contacto na ficha da unidade hidráulica":
        "Poor contact on the hydraulic unit connector",
    "Medidor de massa de ar":
        "Air mass meter",
    "Medidor de massa de ar (G70)":
        "Air mass meter (G70)",
    "Medidor de massa de ar (G70) sujo ou avariado — muito comum":
        "Dirty or faulty air mass meter (G70) — very common",
    "Medidor de massa de ar desviado":
        "Air mass meter out of calibration",
    "Medidor de massa de ar — circuito":
        "Air mass meter — circuit",
    "Medidor de massa de ar — gama/funcionamento":
        "Air mass meter — range/performance",
    "Medidor de massa de ar — sinal alto":
        "Air mass meter — signal high",
    "Medidor de massa de ar — sinal baixo":
        "Air mass meter — signal low",
    "Medir a resistência da N75 (~14–20 Ω em muitos TDI)":
        "Measure the N75 resistance (~14–20 Ω on many TDIs)",
    "Medir a resistência da bobina do injector e comparar com os outros cilindros":
        "Measure the injector coil resistance and compare it with the other cylinders",
    "Medir a resistência de cada vela (< 2 Ω)":
        "Measure the resistance of each glow plug (< 2 Ω)",
    "Medir a resistência do G28 (~1 kΩ em muitos motores)":
        "Measure the G28 resistance (~1 kΩ on many engines)",
    "Medir a resistência do sensor (indutivo ~1–2 kΩ) e o isolamento à massa":
        "Measure the sensor resistance (inductive ~1–2 kΩ) and its insulation to ground",
    "Medir a tensão com motor a 2000 rpm: não deve passar de ~14,8 V":
        "Measure the voltage with the engine at 2000 rpm: it should not exceed ~14.8 V",
    "Medir a tensão da bateria em repouso (~12,6 V) e com motor a trabalhar (13,8–14,5 V)":
        "Measure the battery voltage at rest (~12.6 V) and with the engine running (13.8–14.5 V)",
    "Medir alimentação e massa na ficha da unidade hidráulica":
        "Measure supply and ground at the hydraulic unit connector",
    "Metanol":
        "Methanol",
    "Microcontrolador do cabo (tramas 53/4D)":
        "Cable microcontroller (53/4D frames)",
    "Mistura":
        "Mixture",
    "Mistura demasiado pobre (banco 1)":
        "Mixture too lean (bank 1)",
    "Mistura demasiado pobre (banco 2)":
        "Mixture too lean (bank 2)",
    "Mistura demasiado pobre ao ralenti (banco 1)":
        "Mixture too lean at idle (bank 1)",
    "Mistura demasiado rica (banco 1)":
        "Mixture too rich (bank 1)",
    "Mistura demasiado rica (banco 2)":
        "Mixture too rich (bank 2)",
    "Motor":
        "Engine",
    "Motor / transmissão":
        "Engine / transmission",
    "Motor da bomba avariado":
        "Faulty pump motor",
    "Motor da bomba de retorno gripado ou com escovas gastas":
        "Return pump motor seized or with worn brushes",
    "Motor pode entrar em modo de emergência (ralenti elevado)":
        "The engine may go into limp mode (high idle)",
    "Motor pode não pegar ou ir abaixo — verificar antes de mais nada":
        "The engine may not start or may stall — check this first",
    "Motor quente (líquido acima de 80 °C), ao ralenti e sem consumidores ligados (A/C, luzes, ventilador). A leitura dura 20 segundos.":
        "Warm engine (coolant above 80 °C), at idle and with no consumers on (A/C, lights, fan). The reading lasts 20 seconds.",
    "Média":
        "Medium",
    "Módulo das velas de incandescência — circuito de comando":
        "Glow plug module — control circuit",
    "Módulo de conforto":
        "Comfort module",
    "Módulo de fecho dianteiro do condutor (F220)":
        "Driver front door lock module (F220)",
    "Módulo de fecho dianteiro do passageiro (F221)":
        "Passenger front door lock module (F221)",
    "N75 avariada":
        "Faulty N75",
    "N75 ou tubos de vácuo":
        "N75 or vacuum hoses",
    "Navegação":
        "Navigation",
    "Nenhuma avaria detectada":
        "No fault detected",
    "Nome do sistema / motor":
        "System / engine name",
    "Norma OBD do veículo":
        "Vehicle OBD standard",
    "Normalmente basta apagar; se voltar sem motivo, verificar o sensor de rotação":
        "Clearing is usually enough; if it comes back for no reason, check the engine speed sensor",
    "Não implementado":
        "Not implemented",
    "Não implementado.":
        "Not implemented.",
    "Nível de combustível":
        "Fuel level",
    "Nível de combustível demasiado baixo":
        "Fuel level too low",
    "Nível de líquido baixo (sensor no ar)":
        "Low fluid level (sensor in air)",
    "Número de peça (fabricante)":
        "Part number (manufacturer)",
    "Número de série da centralina":
        "ECU serial number",
    "Número do hardware (fabricante)":
        "Hardware number (manufacturer)",
    "Número do hardware (fornecedor)":
        "Hardware number (supplier)",
    "Número do software (fabricante)":
        "Software number (manufacturer)",
    "Número do software (fornecedor)":
        "Software number (supplier)",
    "O carro registou uma colisão com disparo — a unidade de airbag tem de ser substituída":
        "The car recorded a crash with deployment — the airbag unit must be replaced",
    "OBD (EPA)":
        "OBD (EPA)",
    "OBD e OBD-II":
        "OBD and OBD-II",
    "OBD-I":
        "OBD-I",
    "OBD-II (CARB)":
        "OBD-II (CARB)",
    "OBD-II / EOBD em ISO 15765-4 CAN (11 e 29 bits)":
        "OBD-II / EOBD over ISO 15765-4 CAN (11 and 29 bits)",
    "OBD-II em linha K (ISO 9141-2, ISO 14230-4) e SAE J1850":
        "OBD-II over K-line (ISO 9141-2, ISO 14230-4) and SAE J1850",
    "OBDBr-1":
        "OBDBr-1",
    "OBDBr-2":
        "OBDBr-2",
    "Os mesmos serviços OBD-II (o adaptador escolhe o protocolo)":
        "The same OBD-II services (the adapter chooses the protocol)",
    "Outra unidade foi substituída e a codificação ficou desactualizada":
        "Another unit was replaced and the coding is now out of date",
    "Painel de instrumentos":
        "Instrument cluster",
    "Parcial":
        "Partial",
    "Pedal D":
        "Pedal D",
    "Pedal E":
        "Pedal E",
    "Pedal do acelerador":
        "Accelerator pedal",
    "Perda de comunicação com a unidade da caixa (TCM)":
        "Lost communication with the gearbox unit (TCM)",
    "Perda de comunicação com a unidade do ABS":
        "Lost communication with the ABS unit",
    "Perda de comunicação com a unidade do motor (ECM/PCM A)":
        "Lost communication with the engine unit (ECM/PCM A)",
    "Perda de comunicação com o módulo da carroçaria (BCM)":
        "Lost communication with the body control module (BCM)",
    "Perda de comunicação com o painel de instrumentos":
        "Lost communication with the instrument cluster",
    "Porta passageiro":
        "Passenger door",
    "Porta traseira direita":
        "Rear right door",
    "Porta traseira esquerda":
        "Rear left door",
    "Posição absoluta da borboleta":
        "Absolute throttle position",
    "Posição absoluta da borboleta B":
        "Absolute throttle position B",
    "Posição do pedal do acelerador D":
        "Accelerator pedal position D",
    "Posição do pedal do acelerador E":
        "Accelerator pedal position E",
    "Posição relativa da borboleta":
        "Relative throttle position",
    "Potenciómetro da borboleta gasto":
        "Worn throttle potentiometer",
    "Potenciómetro do pedal do acelerador gasto":
        "Worn accelerator pedal potentiometer",
    "Pressão abaixo da pretendida: fugas, N75, turbo gasto":
        "Pressure below specified: leaks, N75, worn turbo",
    "Pressão absoluta no colector de admissão":
        "Intake manifold absolute pressure",
    "Pressão acima da pretendida: geometria presa, N75":
        "Pressure above specified: stuck geometry, N75",
    "Pressão atm.":
        "Atm. pressure",
    "Pressão atmosférica":
        "Atmospheric pressure",
    "Pressão comb.":
        "Fuel press.",
    "Pressão de combustível baixa":
        "Low fuel pressure",
    "Pressão de combustível incorrecta":
        "Incorrect fuel pressure",
    "Pressão do combustível (relativa)":
        "Fuel pressure (gauge)",
    "Pressão do combustível na rampa demasiado alta":
        "Fuel rail pressure too high",
    "Pressão do combustível na rampa demasiado baixa":
        "Fuel rail pressure too low",
    "Pressão do turbo":
        "Boost pressure",
    "Pressão do turbo excessiva (sobrepressão)":
        "Excessive boost pressure (overboost)",
    "Pressão do turbo insuficiente":
        "Insufficient boost pressure",
    "Pressão do turbo pretendida":
        "Specified boost pressure",
    "Pressão do turbo real":
        "Actual boost pressure",
    "Pressão do turbo — limite superior excedido":
        "Boost pressure — upper limit exceeded",
    "Pressão dos pneus":
        "Tyre pressure",
    "Pressão na rampa (relativa ao vácuo do colector)":
        "Rail pressure (relative to manifold vacuum)",
    "Pressão na rampa de combustível (diesel / injecção directa)":
        "Fuel rail pressure (diesel / direct injection)",
    "Pressão no colector":
        "Manifold pressure",
    "Pressão no colector / massa de ar — incoerente com a posição da borboleta":
        "Manifold pressure / air mass — inconsistent with throttle position",
    "Pressão no colector / pressão atmosférica — incoerência":
        "Manifold pressure / barometric pressure — inconsistency",
    "Pressão no colector de admissão":
        "Intake manifold pressure",
    "Pressão rampa":
        "Rail press.",
    "Pressão rampa rel.":
        "Rail press. rel.",
    "Processador da unidade de comando":
        "Control unit processor",
    "Procurar fugas de vácuo (tubos, juntas)":
        "Look for vacuum leaks (hoses, gaskets)",
    "Programação de chaves":
        "Key programming",
    "Programação errada":
        "Incorrect programming",
    "Programação errada: confirme a codificação/adaptação da unidade.":
        "Incorrect programming: confirm the unit's coding/adaptation.",
    "Propano":
        "Propane",
    "Protocolo do equipamento não documentado. A alternativa legítima é um adaptador aberto (ELM327, KKL) ou uma interface J2534.":
        "Undocumented device protocol. The legitimate alternative is an open adapter (ELM327, KKL) or a J2534 interface.",
    "Pré-aquecimento":
        "Pre-heating",
    "QUENTE":
        "HOT",
    "Ralenti":
        "Idle",
    "Ralenti — rotação abaixo do esperado":
        "Idle — engine speed lower than expected",
    "Ralenti — rotação acima do esperado":
        "Idle — engine speed higher than expected",
    "Raramente: sinal de rotação com interferência":
        "Rarely: engine speed signal with interference",
    "Recirculação de gases de escape (EGR) — circuito de comando":
        "Exhaust gas recirculation (EGR) — control circuit",
    "Recirculação de gases de escape (EGR) — fluxo":
        "Exhaust gas recirculation (EGR) — flow",
    "Recirculação de gases de escape (EGR) — fluxo excessivo":
        "Exhaust gas recirculation (EGR) — excessive flow",
    "Recirculação de gases de escape (EGR) — fluxo insuficiente":
        "Exhaust gas recirculation (EGR) — insufficient flow",
    "Rede / comunicação":
        "Network / communication",
    "Rede de bordo":
        "On-board electrical system",
    "Refrigerante do A/C":
        "A/C refrigerant",
    "Regulador da quantidade de injecção (N146)":
        "Fuel quantity actuator (N146)",
    "Regulador de pressão do combustível 1 — funcionamento":
        "Fuel pressure regulator 1 — performance",
    "Regulador de quantidade (N146) na bomba injectora com desgaste":
        "Worn quantity actuator (N146) in the injection pump",
    "Regulador do alternador avariado (sobrecarga)":
        "Faulty alternator regulator (overcharging)",
    "Regulação da pressão do turbo — desvio negativo":
        "Boost pressure control — negative deviation",
    "Regulação da pressão do turbo — desvio positivo":
        "Boost pressure control — positive deviation",
    "Regulação de distância (ACC)":
        "Distance control (ACC)",
    "Regulação de nível":
        "Level control",
    "Regulação do início de injecção":
        "Start of injection control",
    "Regulação lambda":
        "Lambda control",
    "Relação ar/combustível comandada (lambda)":
        "Commanded air/fuel ratio (lambda)",
    "Relé da bomba de combustível (J17)":
        "Fuel pump relay (J17)",
    "Relé da bomba de combustível com soldaduras fissuradas (muito comum)":
        "Fuel pump relay with cracked solder joints (very common)",
    "Relé das velas":
        "Glow plug relay",
    "Resistência demasiado alta":
        "Resistance too high",
    "Resistência demasiado alta: mau contacto, terminal oxidado ou componente interrompido.":
        "Resistance too high: poor contact, corroded terminal or open component.",
    "Resistência demasiado baixa":
        "Resistance too low",
    "Resistência demasiado baixa: componente em curto interno.":
        "Resistance too low: component internally shorted.",
    "Resistência do circuito fora de gama por mau contacto":
        "Circuit resistance out of range due to poor contact",
    "Resolver primeiro as outras avarias do ABS":
        "Fix the other ABS faults first",
    "Roda fónica":
        "Tone ring",
    "Ross-Tech HEX-V2 / HEX-NET genuínas":
        "Genuine Ross-Tech HEX-V2 / HEX-NET",
    "Rotação":
        "Engine speed",
    "Rotação do motor":
        "Engine speed",
    "Rotação máxima do motor excedida":
        "Maximum engine speed exceeded",
    "Rotação máxima ultrapassada (redução de mudança, condução)":
        "Maximum engine speed exceeded (downshift, driving)",
    "Rádio":
        "Radio",
    "Saída aberta":
        "Open output",
    "Sem OBD":
        "No OBD",
    "Sem SecurityAccess, escrita, rotinas, controlo de saídas nem programação (por desenho). Identificadores específicos do fabricante não incluídos.":
        "No SecurityAccess, writing, routines, output control or programming (by design). Manufacturer-specific identifiers not included.",
    "Sem comunicação: verifique alimentação, massa e barramento da unidade indicada.":
        "No communication: check the supply, ground and bus of the indicated unit.",
    "Sem interface de programação documentada nem autorização do fabricante.":
        "No documented programming interface or manufacturer authorisation.",
    "Sem sinal":
        "No signal",
    "Sem sinal: ficha desligada, fio cortado ou componente sem alimentação.":
        "No signal: connector unplugged, cut wire or component without supply.",
    "Sem validação com um ELM327 físico nem num carro. Clones baratos podem não implementar todos os comandos (os opcionais são ignorados e registados).":
        "Not validated with a physical ELM327 or on a car. Cheap clones may not implement every command (optional ones are ignored and logged).",
    "Sem validação física com um cabo KKL (o proprietário ainda não tem um). A leitura de avarias foi validada contra a resposta real de um Audi A3 8L 1.9 TDI capturada por USBPcap.":
        "Not physically validated with a KKL cable (the owner does not have one yet). Fault reading was validated against the real answer of an Audi A3 8L 1.9 TDI captured with USBPcap.",
    "Sensor Hall (G40)":
        "Hall sensor (G40)",
    "Sensor Hall (G40) avariado":
        "Faulty Hall sensor (G40)",
    "Sensor da válvula EGR — sinal baixo":
        "EGR valve sensor — signal low",
    "Sensor de detonação 1 (G61)":
        "Knock sensor 1 (G61)",
    "Sensor de detonação 1 (banco 1) — circuito":
        "Knock sensor 1 (bank 1) — circuit",
    "Sensor de detonação com binário de aperto errado":
        "Knock sensor with wrong tightening torque",
    "Sensor de gama da transmissão — circuito":
        "Transmission range sensor — circuit",
    "Sensor de nível/temperatura do óleo (G266)":
        "Oil level/temperature sensor (G266)",
    "Sensor de posição da borboleta (G69)":
        "Throttle position sensor (G69)",
    "Sensor de posição da borboleta / pedal A — circuito":
        "Throttle / pedal position sensor A — circuit",
    "Sensor de posição da borboleta / pedal A — gama/funcionamento":
        "Throttle / pedal position sensor A — range/performance",
    "Sensor de posição da borboleta / pedal A — sinal alto":
        "Throttle / pedal position sensor A — signal high",
    "Sensor de posição da borboleta / pedal A — sinal baixo":
        "Throttle / pedal position sensor A — signal low",
    "Sensor de posição da borboleta/pedal — sinal alto":
        "Throttle/pedal position sensor — signal high",
    "Sensor de posição da borboleta/pedal — sinal baixo":
        "Throttle/pedal position sensor — signal low",
    "Sensor de posição da cambota A — circuito":
        "Crankshaft position sensor A — circuit",
    "Sensor de posição da árvore de cames A (banco 1) — circuito":
        "Camshaft position sensor A (bank 1) — circuit",
    "Sensor de posição das borboletas do colector (banco 1) — gama/funcionamento":
        "Intake manifold runner position sensor (bank 1) — range/performance",
    "Sensor de pressão da rampa de combustível — circuito":
        "Fuel rail pressure sensor — circuit",
    "Sensor de pressão da rampa de combustível — gama/funcionamento":
        "Fuel rail pressure sensor — range/performance",
    "Sensor de pressão da rampa de combustível — sinal alto":
        "Fuel rail pressure sensor — signal high",
    "Sensor de pressão da rampa de combustível — sinal baixo":
        "Fuel rail pressure sensor — signal low",
    "Sensor de pressão do colector (MAP) avariado":
        "Faulty manifold pressure (MAP) sensor",
    "Sensor de pressão do colector (MAP) — circuito":
        "Manifold pressure (MAP) sensor — circuit",
    "Sensor de pressão do colector (MAP) — gama/funcionamento":
        "Manifold pressure (MAP) sensor — range/performance",
    "Sensor de pressão do colector (MAP) — sinal alto":
        "Manifold pressure (MAP) sensor — signal high",
    "Sensor de pressão do colector (MAP) — sinal baixo":
        "Manifold pressure (MAP) sensor — signal low",
    "Sensor de pressão do filtro de partículas A — circuito":
        "Particulate filter pressure sensor A — circuit",
    "Sensor de pressão do turbo":
        "Boost pressure sensor",
    "Sensor de pressão do turbo — gama/funcionamento":
        "Boost pressure sensor — range/performance",
    "Sensor de pressão do turbo — sinal alto":
        "Boost pressure sensor — signal high",
    "Sensor de pressão do turbo — sinal baixo":
        "Boost pressure sensor — signal low",
    "Sensor de rotação (G28) avariado ou sujo":
        "Faulty or dirty engine speed sensor (G28)",
    "Sensor de rotação do motor (G28)":
        "Engine speed sensor (G28)",
    "Sensor de temperatura (G62) avariado — muito comum":
        "Faulty temperature sensor (G62) — very common",
    "Sensor de temperatura do ar avariado":
        "Faulty air temperature sensor",
    "Sensor de temperatura do ar de admissão (G42)":
        "Intake air temperature sensor (G42)",
    "Sensor de temperatura do ar de admissão — circuito":
        "Intake air temperature sensor — circuit",
    "Sensor de temperatura do ar de admissão — sinal alto":
        "Intake air temperature sensor — signal high",
    "Sensor de temperatura do ar de admissão — sinal baixo":
        "Intake air temperature sensor — signal low",
    "Sensor de temperatura do líquido de refrigeração (G2)":
        "Coolant temperature sensor (G2)",
    "Sensor de temperatura do líquido de refrigeração (G62)":
        "Coolant temperature sensor (G62)",
    "Sensor de temperatura do líquido de refrigeração — circuito":
        "Coolant temperature sensor — circuit",
    "Sensor de temperatura do líquido de refrigeração — gama/funcionamento":
        "Coolant temperature sensor — range/performance",
    "Sensor de temperatura do líquido de refrigeração — sinal alto":
        "Coolant temperature sensor — signal high",
    "Sensor de temperatura do líquido de refrigeração — sinal baixo":
        "Coolant temperature sensor — signal low",
    "Sensor de temperatura exterior (G17)":
        "Outside temperature sensor (G17)",
    "Sensor de temperatura exterior (para-choques) partido ou com humidade":
        "Outside temperature sensor (bumper) broken or damp",
    "Sensor de velocidade ABS dianteiro dir. (G45)":
        "Front right ABS speed sensor (G45)",
    "Sensor de velocidade ABS dianteiro esq. (G47)":
        "Front left ABS speed sensor (G47)",
    "Sensor de velocidade ABS traseiro dir. (G44)":
        "Rear right ABS speed sensor (G44)",
    "Sensor de velocidade ABS traseiro esq. (G46)":
        "Rear left ABS speed sensor (G46)",
    "Sensor de velocidade da roda dianteira direita — circuito":
        "Front right wheel speed sensor — circuit",
    "Sensor de velocidade da roda dianteira esquerda — circuito":
        "Front left wheel speed sensor — circuit",
    "Sensor de velocidade da roda traseira direita — circuito":
        "Rear right wheel speed sensor — circuit",
    "Sensor de velocidade da roda traseira esquerda — circuito":
        "Rear left wheel speed sensor — circuit",
    "Sensor de velocidade de entrada / turbina — circuito":
        "Input / turbine speed sensor — circuit",
    "Sensor de velocidade do veículo":
        "Vehicle speed sensor",
    "Sensor de velocidade do veículo (G68)":
        "Vehicle speed sensor (G68)",
    "Sensor de velocidade do veículo A":
        "Vehicle speed sensor A",
    "Sensor de velocidade do veículo — gama/funcionamento":
        "Vehicle speed sensor — range/performance",
    "Sensor de velocidade sujo ou com folga (limalha no íman)":
        "Speed sensor dirty or loose (metal filings on the magnet)",
    "Sensor do nível de combustível (G)":
        "Fuel level sensor (G)",
    "Sensor do pedal do acelerador (G79)":
        "Accelerator pedal sensor (G79)",
    "Sensor do pistão modulador":
        "Modulating piston sensor",
    "Sensor do pistão modulador (G149)":
        "Modulating piston sensor (G149)",
    "Sensor do ângulo de direcção (G85)":
        "Steering angle sensor (G85)",
    "Sensor dos gases de escape":
        "Exhaust gas sensor",
    "Serviços e limitações":
        "Services and limitations",
    "Sessão de diagnóstico activa":
        "Active diagnostic session",
    "Sinal de reconhecimento de mudança":
        "Gear recognition signal",
    "Sinal de rotação do motor":
        "Engine speed signal",
    "Sinal de temperatura exterior do painel de instrumentos":
        "Instrument cluster outside temperature signal",
    "Sinal de velocidade":
        "Speed signal",
    "Sinal demasiado alto":
        "Signal too high",
    "Sinal demasiado alto: sensor desligado (puxa para a alimentação) ou valor real fora de gama.":
        "Signal too high: sensor unplugged (pulled up to supply) or real value out of range.",
    "Sinal demasiado baixo":
        "Signal too low",
    "Sinal demasiado baixo: curto à massa, alimentação do sensor em falta ou valor real fora de gama.":
        "Signal too low: short to ground, missing sensor supply or real value out of range.",
    "Sinal fora de especificação":
        "Signal outside specification",
    "Sinal fora de especificação: compare com os valores de medição e com um componente de referência.":
        "Signal outside specification: compare with the measuring values and with a reference component.",
    "Sinal não plausível":
        "Implausible signal",
    "Sinal não plausível (2)":
        "Implausible signal (2)",
    "Sinal não plausível: o valor não bate certo com outros sensores — sensor degradado ou mau contacto.":
        "Implausible signal: the value does not match other sensors — degraded sensor or poor contact.",
    "Sintonizador TV":
        "TV tuner",
    "Sistema EVAP — fuga grande detectada":
        "EVAP system — large leak detected",
    "Sistema EVAP — fuga pequena detectada":
        "EVAP system — small leak detected",
    "Sistema de ajuste de combustível — mistura pobre (banco 1)":
        "Fuel trim system — lean (bank 1)",
    "Sistema de ajuste de combustível — mistura rica (banco 1)":
        "Fuel trim system — rich (bank 1)",
    "Sistema de comando da transmissão (pedido de luz de avaria)":
        "Transmission control system (MIL request)",
    "Sistema de combustível":
        "Fuel system",
    "Sistema de controlo da caixa automática":
        "Automatic gearbox control system",
    "Sistema de controlo de evaporação (EVAP)":
        "Evaporative emission control system (EVAP)",
    "Sistema de controlo do ralenti":
        "Idle control system",
    "Sistema de emissões evaporativas":
        "Evaporative emission system",
    "Sistema de evaporação":
        "Evaporative system",
    "Sistema de som":
        "Sound system",
    "Sobrepressão do turbo":
        "Turbo overboost",
    "Sobrepressão — ver P0234":
        "Overboost — see P0234",
    "Sonda lambda":
        "Oxygen sensor",
    "Sonda lambda (G39)":
        "Oxygen sensor (G39)",
    "Sonda lambda (banco 1, sensor 1) — circuito":
        "Oxygen sensor (bank 1, sensor 1) — circuit",
    "Sonda lambda (banco 1, sensor 1) — resposta lenta":
        "Oxygen sensor (bank 1, sensor 1) — slow response",
    "Sonda lambda (banco 1, sensor 1) — sem actividade":
        "Oxygen sensor (bank 1, sensor 1) — no activity",
    "Sonda lambda (banco 1, sensor 1) — tensão alta":
        "Oxygen sensor (bank 1, sensor 1) — high voltage",
    "Sonda lambda (banco 1, sensor 1) — tensão baixa":
        "Oxygen sensor (bank 1, sensor 1) — low voltage",
    "Sonda lambda (banco 1, sensor 2) — circuito":
        "Oxygen sensor (bank 1, sensor 2) — circuit",
    "Sonda lambda envelhecida ou contaminada":
        "Aged or contaminated oxygen sensor",
    "Sonda lambda lenta":
        "Slow oxygen sensor",
    "Sonda lambda posterior a ler mal":
        "Downstream oxygen sensor reading incorrectly",
    "Substituir o vedante/clip ao trocar o sensor":
        "Replace the seal/clip when changing the sensor",
    "Só detecção e explicação":
        "Detection and explanation only",
    "Tejadilho eléctrico":
        "Electric sunroof",
    "Telemática":
        "Telematics",
    "Temp. ambiente":
        "Ambient temp.",
    "Temp. ar":
        "Air temp.",
    "Temp. cat.":
        "Cat. temp.",
    "Temp. líquido":
        "Coolant temp.",
    "Temp. óleo":
        "Oil temp.",
    "Temperatura ambiente":
        "Ambient temperature",
    "Temperatura do ar de admissão":
        "Intake air temperature",
    "Temperatura do catalisador — banco 1, sensor 1":
        "Catalyst temperature — bank 1, sensor 1",
    "Temperatura do líquido":
        "Coolant temperature",
    "Temperatura do líquido de refrigeração":
        "Coolant temperature",
    "Temperatura do óleo do motor":
        "Engine oil temperature",
    "Tempo c/ MIL":
        "Time w/ MIL",
    "Tempo com a luz de avaria acesa":
        "Time with the malfunction indicator on",
    "Tempo de criação de pressão dianteiro demasiado longo":
        "Front pressure build-up time too long",
    "Tempo de criação de pressão traseiro demasiado longo":
        "Rear pressure build-up time too long",
    "Tempo de injecção":
        "Injection time",
    "Tempo de redução de pressão dianteiro demasiado longo":
        "Front pressure reduction time too long",
    "Tempo de redução de pressão traseiro demasiado longo":
        "Rear pressure reduction time too long",
    "Tempo desde apagar":
        "Time since clear",
    "Tempo desde o arranque":
        "Time since engine start",
    "Tempo desde que as avarias foram apagadas":
        "Time since faults were cleared",
    "Tempo motor":
        "Run time",
    "Tensão ECU":
        "ECU voltage",
    "Tensão da bateria":
        "Battery voltage",
    "Tensão da unidade de comando":
        "Control module voltage",
    "Tensão de alimentação B+":
        "B+ supply voltage",
    "Tensão de alimentação baixa":
        "Low supply voltage",
    "Tensão de alimentação muito baixa durante a leitura":
        "Supply voltage very low during reading",
    "Tensão de alimentação terminal 30":
        "Terminal 30 supply voltage",
    "Tensão do sistema":
        "System voltage",
    "Tensão do sistema alta":
        "System voltage high",
    "Tensão do sistema baixa":
        "System voltage low",
    "Termóstato — temperatura do líquido abaixo da temperatura de regulação":
        "Thermostat — coolant temperature below regulating temperature",
    "Testado com simulador":
        "Tested with simulator",
    "Testar com resistência de simulação (~2–3 Ω) no lugar do detonador — nunca medir o airbag com multímetro":
        "Test with a simulation resistor (~2–3 Ω) in place of the igniter — never measure the airbag with a multimeter",
    "Teste de carga à bateria":
        "Battery load test",
    "Teste de fumo à admissão":
        "Smoke test of the intake",
    "Teste de fumo/pressão ao circuito de admissão":
        "Smoke/pressure test of the intake circuit",
    "Teste de saídas":
        "Output tests",
    "Teste de saídas no ABS (03)":
        "Output tests on the ABS (03)",
    "Teste de saídas no motor (01)":
        "Output tests on the engine (01)",
    "Teste de saídas no motor (01): ouvir o relé":
        "Output tests on the engine (01): listen for the relay",
    "Teste de saídas: deve ouvir-se o clique da válvula":
        "Output tests: you should hear the valve click",
    "Teste guiado 'Equilíbrio dos injectores' (grupo 013) em motores TDI":
        "Guided test 'Injector balance' (group 013) on TDI engines",
    "Teste guiado 'Pressão do turbo' (grupo 011) a acelerar em 3.ª":
        "Guided test 'Boost pressure' (group 011) accelerating in 3rd gear",
    "Tipo de combustível":
        "Fuel type",
    "Tracção integral":
        "All-wheel drive",
    "Tracção integral (Haldex)":
        "All-wheel drive (Haldex)",
    "Travão de estacionamento":
        "Parking brake",
    "Travões / ABS":
        "Brakes / ABS",
    "Trocar bobinas entre cilindros e ver se a falha acompanha":
        "Swap coils between cylinders and see if the misfire follows",
    "Trocar o relé por um igual e testar":
        "Replace the relay with an identical one and test",
    "Tubos de vácuo":
        "Vacuum hoses",
    "Tubos de vácuo rachados ou trocados":
        "Cracked or swapped vacuum hoses",
    "Turbo / admissão":
        "Turbo / intake",
    "UDS / ISO 14229 (leitura) sobre CAN":
        "UDS / ISO 14229 (read) over CAN",
    "Unidade de comando":
        "Control unit",
    "Unidade de comando avariada":
        "Faulty control unit",
    "Unidade de comando avariada: confirme alimentação e massas antes de a substituir.":
        "Faulty control unit: confirm supply and grounds before replacing it.",
    "Unidade de comando da borboleta (J338)":
        "Throttle valve control module (J338)",
    "Unidade de comando da caixa":
        "Gearbox control unit",
    "Unidade de comando da porta do condutor (J386)":
        "Driver door control unit (J386)",
    "Unidade de comando da porta do passageiro (J387)":
        "Passenger door control unit (J387)",
    "Unidade de comando da porta traseira direita (J389)":
        "Rear right door control unit (J389)",
    "Unidade de comando da porta traseira esquerda (J388)":
        "Rear left door control unit (J388)",
    "Unidade de comando do ABS":
        "ABS control unit",
    "Unidade de comando do motor":
        "Engine control unit",
    "Unidade de comando do motor (imobilizador)":
        "Engine control unit (immobiliser)",
    "Unidade de comando do motor bloqueada (imobilizador)":
        "Engine control unit locked (immobiliser)",
    "Unidade de comando do motor substituída sem adaptação ao imobilizador":
        "Engine control unit replaced without immobiliser adaptation",
    "Unidade de comando dos airbags (J234)":
        "Airbag control unit (J234)",
    "Unidade de comando mal codificada":
        "Control unit incorrectly coded",
    "Unidade de comando no painel de instrumentos (J285)":
        "Control unit in instrument cluster (J285)",
    "Unidade de comando nova ou substituída ainda sem codificação":
        "New or replaced control unit not coded yet",
    "Unidade de comando não codificada":
        "Control unit not coded",
    "Unidade de comando referida sem alimentação ou sem massa":
        "Indicated control unit without supply or ground",
    "Unidade de comando — avaria interna no controlo de detonação":
        "Control unit — internal knock control fault",
    "Unidade de comando — erro de soma de verificação da memória interna":
        "Control unit — internal memory checksum error",
    "Unidade de comando — processador":
        "Control unit — processor",
    "Unidade de comando/visor":
        "Control/display unit",
    "Validado com dados reais capturados":
        "Validated with real captured data",
    "Valores de medição de falhas de ignição por cilindro":
        "Measuring values for misfires per cylinder",
    "Valores de medição do painel (17) grupo 081/022: estado do imobilizador e da chave":
        "Instrument cluster (17) measuring values group 081/022: immobiliser and key status",
    "Valores de medição do painel (17): nível de combustível e resistência":
        "Instrument cluster (17) measuring values: fuel level and resistance",
    "Valores de medição grupo 001 campo 3: tensão do pistão modulador":
        "Measuring values group 001 field 3: modulating piston voltage",
    "Valores de medição grupo 001: comparar a velocidade das 4 rodas a andar devagar":
        "Measuring values group 001: compare the speed of all 4 wheels while driving slowly",
    "Valores de medição grupo 001: rotação ao arranque (deve aparecer > 0)":
        "Measuring values group 001: engine speed while cranking (should be > 0)",
    "Valores de medição grupo 003: massa de ar real vs pretendida":
        "Measuring values group 003: actual vs specified air mass",
    "Valores de medição grupo 003: massa de ar real vs pretendida e ciclo EGR":
        "Measuring values group 003: actual vs specified air mass and EGR duty cycle",
    "Valores de medição grupo 004: início de injecção pretendido vs real":
        "Measuring values group 004: specified vs actual start of injection",
    "Valores de medição: atraso de ignição por cilindro":
        "Measuring values: ignition retard per cylinder",
    "Valores de medição: correcções de mistura (adaptações) ao ralenti e em carga":
        "Measuring values: fuel trims (adaptations) at idle and under load",
    "Valores de medição: percentagem do pedal deve variar suavemente 0–100 %":
        "Measuring values: the pedal percentage should change smoothly 0–100 %",
    "Valores de medição: tensão da sonda deve oscilar 0,1–0,9 V ao ralenti quente":
        "Measuring values: the sensor voltage should oscillate 0.1–0.9 V at warm idle",
    "Valores de medição: ângulo da borboleta sem acelerar":
        "Measuring values: throttle angle without accelerating",
    "Vela de incandescência queimada":
        "Burnt-out glow plug",
    "Velas de incandescência — circuito A":
        "Glow plugs — circuit A",
    "Velas/bobinas gastas":
        "Worn spark plugs/coils",
    "Velocidade demasiado alta":
        "Speed too high",
    "Velocidade demasiado baixa":
        "Speed too low",
    "Velocidade do veículo":
        "Vehicle speed",
    "Ventilador de arrefecimento 1 — circuito de comando":
        "Cooling fan 1 — control circuit",
    "Verificar a cablagem entre a unidade de comando e o injector":
        "Check the wiring between the control unit and the injector",
    "Verificar a ficha do painel de instrumentos":
        "Check the instrument cluster connector",
    "Verificar a haste de comando do turbo":
        "Check the turbo actuator rod",
    "Verificar a pressão de combustível":
        "Check the fuel pressure",
    "Verificar a tensão da bateria":
        "Check the battery voltage",
    "Verificar alimentação 5 V do sensor":
        "Check the sensor's 5 V supply",
    "Verificar alimentação e massas da unidade":
        "Check the unit's supply and grounds",
    "Verificar fichas amarelas debaixo dos bancos e no volante":
        "Check the yellow connectors under the seats and in the steering wheel",
    "Verificar fugas no colector de escape":
        "Check for exhaust manifold leaks",
    "Verificar fusíveis do ABS":
        "Check the ABS fuses",
    "Verificar fusíveis e alimentação da unidade indicada":
        "Check the fuses and supply of the indicated unit",
    "Verificar fusível grande da bomba ABS":
        "Check the ABS pump's large fuse",
    "Verificar o estado do contacto S nos valores de medição do painel":
        "Check the S contact status in the instrument cluster measuring values",
    "Verificar o nível de líquido de refrigeração":
        "Check the coolant level",
    "Verificar tubos da admissão e intercooler":
        "Check the intake and intercooler hoses",
    "Verificar tubos de vácuo":
        "Check the vacuum hoses",
    "Versão do firmware, modo de arranque, teste da linha K feito pelo cabo, repor modo de origem":
        "Firmware version, start-up mode, K-line test done by the cable, restore original mode",
    "Versão do hardware (fornecedor)":
        "Hardware version (supplier)",
    "Versão do software (fabricante)":
        "Software version (manufacturer)",
    "Versão do software (fornecedor)":
        "Software version (supplier)",
    "Vigilância do habitáculo":
        "Interior monitoring",
    "Válvula EGR (N18)":
        "EGR valve (N18)",
    "Válvula EGR presa com carvão":
        "EGR valve stuck with carbon",
    "Válvula EGR — gama/funcionamento":
        "EGR valve — range/performance",
    "Válvula de comando da pressão do turbo — circuito aberto":
        "Boost pressure control valve — open circuit",
    "Válvula de comando da pressão do turbo — gama/funcionamento":
        "Boost pressure control valve — range/performance",
    "Válvula de controlo do ralenti (N71)":
        "Idle air control valve (N71)",
    "Válvula de início de injecção (N108) avariada":
        "Faulty start of injection valve (N108)",
    "Válvula de ralenti suja ou presa":
        "Dirty or stuck idle valve",
    "Válvula do ar secundário (N112)":
        "Secondary air valve (N112)",
    "Válvula do início de injecção (N108)":
        "Start of injection valve (N108)",
    "WWH OBD":
        "WWH OBD",
    "alargada":
        "extended",
    "circuito aberto":
        "open circuit",
    "confirmada (memorizada)":
        "confirmed (stored)",
    "controlo auxiliar de emissões":
        "auxiliary emission controls",
    "curto-circuito à bateria":
        "short to battery",
    "curto-circuito à bateria ou circuito aberto":
        "short to battery or open circuit",
    "curto-circuito à massa":
        "short to ground",
    "curto-circuito à massa ou circuito aberto":
        "short to ground or open circuit",
    "código OBD-II (ver manual)":
        "OBD-II code (see manual)",
    "dados série inválidos recebidos":
        "invalid serial data received",
    "falha de algoritmo":
        "algorithm failure",
    "falha de componente":
        "component failure",
    "falha de mensagem de barramento / sinal":
        "bus / signal message failure",
    "falha de plausibilidade do sinal":
        "signal plausibility failure",
    "falha de programação do sistema":
        "system programming failure",
    "falha de sinal FM/PWM":
        "FM/PWM signal failure",
    "falha eléctrica geral":
        "general electrical failure",
    "falha geral de sinal":
        "general signal failure",
    "falha interna do sistema":
        "system internal failure",
    "falha mecânica":
        "mechanical failure",
    "falha na comparação de sinais":
        "signal comparison failure",
    "falha presente agora":
        "test failed now",
    "falhou desde o último apagar":
        "failed since last clear",
    "falhou neste ciclo de condução":
        "failed this drive cycle",
    "medição de ar e combustível":
        "fuel and air metering",
    "medição de ar e combustível (circuito dos injectores)":
        "fuel and air metering (injector circuit)",
    "medição de ar/combustível e emissões auxiliares":
        "fuel/air metering and auxiliary emission controls",
    "mensagem em falta":
        "missing message",
    "normal":
        "default",
    "pede luz de aviso":
        "warning indicator requested",
    "pendente":
        "pending",
    "memorizada":
        "stored",
    "propulsão híbrida":
        "hybrid propulsion",
    "sem informação adicional":
        "no additional information",
    "sinal inválido":
        "invalid signal",
    "sistema de ignição ou falhas de combustão":
        "ignition system or misfire",
    "tensão do circuito abaixo do limite":
        "circuit voltage below threshold",
    "tensão do circuito acima do limite":
        "circuit voltage above threshold",
    "tensão do circuito fora do intervalo":
        "circuit voltage out of range",
    "teste não concluído desde o último apagar":
        "test not completed since last clear",
    "teste não concluído neste ciclo":
        "test not completed this cycle",
    "transmissão":
        "transmission",
    "unidade de comando e saídas auxiliares":
        "control module and auxiliary outputs",
    "velocidade do veículo, ralenti e entradas auxiliares":
        "vehicle speed, idle control and auxiliary inputs",
    "° AAPMS":
        "° ATDC",
    "° APMS":
        "° BTDC",
    "Ângulo da borboleta":
        "Throttle angle",
    "abrir":
        "open",
    "agora":
        "now",
    "apagada":
        "off",
    "completo":
        "complete",
    "fechar":
        "close",
    "incompleto":
        "incomplete",
    "navegar":
        "navigate",
    "Relatório de diagnóstico":
        "Diagnostic report",
    "Resumo":
        "Summary",
    "Adaptador respondeu":
        "Adapter answered",
    "Comunicação com o veículo":
        "Communication with the vehicle",
    "não medida pelo adaptador":
        "not measured by the adapter",
    "{ecu}: {n} parâmetros":
        "{ecu}: {n} parameters",
    "{v:.1f} V (medida pelo adaptador)":
        "{v:.1f} V (measured by the adapter)",
    "{version} a {baud} baud":
        "{version} at {baud} baud",
    " — simulação":
        " — simulation",
    "O controlador recusou a codificação {coding:05d}: continua com {current:05d} (antes: {before:05d}).":
        "The module refused coding {coding:05d}: it still has {current:05d} (before: {before:05d}).",
    "O controlador recusou a codificação {coding:05d}: continua com {current:05d}.":
        "The module refused coding {coding:05d}: it still has {current:05d}.",
    "\n\nA ligação ao veículo faz-se na página OBD — todas as marcas.":
        "\n\nThe connection to the vehicle is made on the OBD — all makes page.",
    " Tensão da bateria na ficha de diagnóstico: {volt:.1f} V.":
        " Battery voltage at the diagnostic socket: {volt:.1f} V.",
    "<p><b>Nenhum cabo de diagnóstico encontrado.</b></p><p>Ligue o cabo à porta USB e volte a carregar em Detectar cabo. Se continuar sem aparecer:</p><ul><li>Experimente outra porta USB (de preferência directamente no PC, sem hub).</li><li>Se o cabo é novo neste PC, ligue o PC à internet uma vez com o cabo ligado: o Windows prepara-o sozinho.</li></ul>":
        "<p><b>No diagnostic cable found.</b></p><p>Plug the cable into a USB port and click Detect cable again. If it still does not appear:</p><ul><li>Try another USB port (preferably directly on the PC, without a hub).</li><li>If the cable is new to this PC, connect the PC to the internet once with the cable plugged in: Windows prepares it by itself.</li></ul>",
    "<p><b>Vai pedir a TODAS as centralinas que apaguem as avarias.</b></p><ul><li>Apaga também as imagens congeladas e repõe os monitores de prontidão (o carro pode chumbar na inspecção até completar um ciclo de condução).</li><li>Ignição ligada e <b>motor desligado</b> — muitas centralinas recusam com o motor a trabalhar.</li><li>As avarias permanentes não se apagam por este pedido.</li></ul><p>Depois do pedido, o programa volta a ler as avarias para confirmar.</p>":
        "<p><b>This asks ALL control units to clear their faults.</b></p><ul><li>It also clears the freeze frames and resets the readiness monitors (the car may fail the inspection until it completes a drive cycle).</li><li>Ignition on and <b>engine off</b> — many control units refuse with the engine running.</li><li>Permanent faults are not cleared by this request.</li></ul><p>After the request, the program reads the faults again to confirm.</p>",
    "<p>Interfaces de diagnóstico instaladas neste PC: <b>{v}</b>. Pode escolhê-las em Porta do cabo.</p>":
        "<p>Diagnostic interfaces installed on this PC: <b>{v}</b>. You can choose them in Cable port.</p>",
    "<p>O cabo foi escolhido e guardado automaticamente.</p>":
        "<p>The cable was selected and saved automatically.</p>",
    "A identificação detalhada não está disponível para esta centralina.":
        "Detailed identification is not available for this control unit.",
    "A ler a identificação da centralina {target}…":
        "Reading the identification of control unit {target}…",
    "A ligar ao veículo (pode demorar até 20 s na primeira vez).":
        "Connecting to the vehicle (can take up to 20 s the first time).",
    "A ligar ao veículo por OBD…":
        "Connecting to the vehicle through OBD…",
    "A ligar por OBD…":
        "Connecting through OBD…",
    "A porta {port_name} abriu, mas o adaptador OBD não respondeu. Confirme que o adaptador está ligado ao PC (ou que o Bluetooth está emparelhado) e que nenhum outro programa o está a usar.":
        "Port {port_name} opened, but the OBD adapter did not answer. Check that the adapter is plugged into the PC (or that Bluetooth is paired) and that no other program is using it.",
    "A porta {port} não existe neste momento":
        "Port {port} does not exist right now",
    "Abrir o adaptador":
        "Open the adapter",
    "Abrir o cabo":
        "Open the cable",
    "Abrir simulador OBD":
        "Open OBD simulator",
    "Adaptador OBD":
        "OBD adapter",
    "Adaptador OBD (todas as marcas)":
        "OBD adapter (all makes)",
    "Adaptador OBD · {port}":
        "OBD adapter · {port}",
    "Adaptador ligado ao PC":
        "Adapter connected to the PC",
    "Ainda não há nenhuma versão publicada.":
        "No version has been published yet.",
    "Auto-Scan interrompido: {v} de {v2} controladores verificados (resultado parcial)":
        "Auto-Scan interrupted: {v} of {v2} modules checked (partial result)",
    "Avarias, luz de avaria, prontidão para a inspecção e dados em tempo real de qualquer marca (gasolina desde 2001 e gasóleo desde 2004 na UE). Mostra só o que o veículo indica que suporta.":
        "Faults, warning light, inspection readiness and live data for any make (petrol from 2001 and diesel from 2004 in the EU). Shows only what the vehicle says it supports.",
    "Avarias, prontidão e dados de qualquer marca":
        "Faults, readiness and data for any make",
    "Avarias, prontidão para a inspecção e dados em tempo real de qualquer marca.":
        "Faults, inspection readiness and live data for any make.",
    "Avarias:":
        "Faults:",
    "Avarias: nenhuma presente, pendente ou confirmada":
        "Faults: none present, pending or confirmed",
    "Avarias: não disponíveis ({dtc_error})":
        "Faults: not available ({dtc_error})",
    "Cabo USB":
        "USB cable",
    "Cabo VAG":
        "VAG cable",
    "Cabo de diagnóstico USB":
        "USB diagnostic cable",
    "Cabo encontrado e pronto":
        "Cable found and ready",
    "Cabo encontrado, mas falta uma parte do programa":
        "Cable found, but part of the program is missing",
    "Cabo encontrado, mas o Windows ainda não o preparou":
        "Cable found, but Windows has not prepared it yet",
    "Cabo encontrado, mas precisa de ser preparado":
        "Cable found, but it needs to be prepared",
    "Cabo escolhido: {port}":
        "Selected cable: {port}",
    "Cabo ligado ao PC":
        "Cable connected to the PC",
    "Cabo ligado ao carro":
        "Cable connected to the car",
    "Cabo por configurar":
        "Cable not set up",
    "Cabo pronto (sem centralina)":
        "Cable ready (no control unit)",
    "Cabo pronto — ainda sem ligação a nenhuma centralina.":
        "Cable ready — not yet connected to any control unit.",
    "Cabo sem resposta":
        "Cable not responding",
    "Cabo, dados da oficina, licença e ecrã.":
        "Cable, workshop details, licence and display.",
    "Cabo: {port}":
        "Cable: {port}",
    "Centralina {target} — identificação detalhada":
        "Control unit {target} — detailed identification",
    "Centralinas":
        "Control units",
    "Com o cabo no carro e a ignição ligada, carregue em Testar ligação.":
        "With the cable in the car and the ignition on, click Test connection.",
    "Descrições: os códigos comuns a todas as marcas têm descrição completa; os códigos próprios de cada marca mostram apenas a categoria.":
        "Descriptions: codes common to all makes have a full description; manufacturer-specific codes show only the category.",
    "Diagnóstico automóvel profissional":
        "Professional vehicle diagnostics",
    "Diagnóstico completo do Grupo VW (VW, Audi, Seat, Škoda) com mapa do veículo e assistente de avarias, e leitura de avarias de qualquer marca — numa só aplicação.":
        "Full diagnostics for the VW Group (VW, Audi, Seat, Škoda) with a vehicle map and fault assistant, plus fault reading for any make — in one application.",
    "Em Opções está escolhido o cabo VAG":
        "The VAG cable is selected in Options",
    "Em Opções, escolha \"Adaptador OBD — todas as marcas\" em Equipamento (ou o Simulador OBD) para usar esta página.":
        "In Options, choose \"OBD adapter — all makes\" under Equipment (or the OBD simulator) to use this page.",
    "Encontrar o cabo ligado ao PC":
        "Find the cable plugged into the PC",
    "Endereço inválido. Exemplos: 01, 17, 46.":
        "Invalid address. Examples: 01, 17, 46.",
    "Equipamento":
        "Equipment",
    "Equipamento não compatível: {name}":
        "Incompatible equipment: {name}",
    "Equipamento: {kind} · {port}":
        "Equipment: {kind} · {port}",
    "Escolha a porta do adaptador OBD em Opções.":
        "Choose the OBD adapter port in Options.",
    "Escolha o adaptador OBD (ou o simulador) em Opções e carregue em Ligar.":
        "Choose the OBD adapter (or the simulator) in Options and click Connect.",
    "Escolha o módulo na lista ou escreva o endereço (ex.: 01 motor, 17 painel).":
        "Choose the module from the list or type its address (e.g. 01 engine, 17 instruments).",
    "Escolha {com} na porta do cabo e carregue em Testar ligação com a ignição ligada.":
        "Choose {com} as the cable port and click Test connection with the ignition on.",
    "Esta função ainda não está disponível para este módulo.":
        "This function is not yet available for this module.",
    "Este adaptador OBD não é compatível com o Roots Auto Doctor.":
        "This OBD adapter is not compatible with Roots Auto Doctor.",
    "Este cabo está num modo que o Roots Auto Doctor ainda não consegue usar. Crie um Pacote de suporte em Opções e envie-o.":
        "This cable is in a mode that Roots Auto Doctor cannot use yet. Create a Support package in Options and send it.",
    "Este cabo precisa de uma preparação única. Crie um Pacote de suporte (em Opções) e envie-o ao suporte.":
        "This cable needs a one-time preparation. Create a Support package (in Options) and send it to support.",
    "Este controlador só comunica com o cabo VAG: ligue-o com o cabo VAG em vez desta interface.":
        "This module only communicates through the VAG cable: connect to it with the VAG cable instead of this interface.",
    "Este equipamento só funciona com o programa do seu fabricante. Use um cabo VAG compatível ou um adaptador OBD.":
        "This equipment only works with its manufacturer's program. Use a compatible VAG cable or an OBD adapter.",
    "Este veículo usa o diagnóstico dos pesados, que ainda não é suportado.":
        "This vehicle uses heavy-duty diagnostics, which are not supported yet.",
    "Está a usar o simulador: os valores e avarias são fictícios.":
        "You are using the simulator: values and faults are fictitious.",
    "Experimentar o diagnóstico de todas as marcas sem carro":
        "Try all-makes diagnostics without a car",
    "Houve um erro na comunicação com o veículo. Tente de novo; se continuar, crie um Pacote de suporte em Opções e envie-o.":
        "There was an error communicating with the vehicle. Try again; if it continues, create a Support package in Options and send it.",
    "Identificação detalhada da centralina (números de peça e de software) e avarias com o tipo de falha. Disponível nos veículos mais recentes.":
        "Detailed control unit identification (part and software numbers) and faults with their failure type. Available on more recent vehicles.",
    "Interface de diagnóstico":
        "Diagnostic interface",
    "Ler identificação detalhada da centralina seleccionada":
        "Read detailed identification of the selected control unit",
    "Ligado ao veículo por OBD":
        "Connected to the vehicle through OBD",
    "Ligado ao veículo por OBD · {n} centralina(s)":
        "Connected to the vehicle through OBD · {n} control unit(s)",
    "Ligado por OBD":
        "Connected through OBD",
    "Ligar ao veículo com o adaptador OBD":
        "Connect to the vehicle with the OBD adapter",
    "Ligar por OBD":
        "Connect through OBD",
    "Ligação ao veículo":
        "Connection to the vehicle",
    "Ligação ao veículo fechada.":
        "Connection to the vehicle closed.",
    "Ligue o PC à internet com o cabo ligado e aguarde um minuto (o Windows prepara-o sozinho), ou volte a instalar o Roots Auto Doctor. Depois carregue outra vez em Detectar cabo.":
        "Connect the PC to the internet with the cable plugged in and wait a minute (Windows prepares it by itself), or reinstall Roots Auto Doctor. Then click Detect cable again.",
    "Ligue o cabo ao carro com a ignição ligada.\n\nMódulo a testar (01 = motor, 17 = painel):":
        "Connect the cable to the car with the ignition on.\n\nModule to test (01 = engine, 17 = instruments):",
    "Ligue o cabo à ficha de diagnóstico do carro e ao PC, e ligue a ignição.":
        "Plug the cable into the car's diagnostic socket and into the PC, and switch the ignition on.",
    "Login enviado e recebido pelo controlador. O controlador não indica se o código está correcto: confirme na função que precisa do login.":
        "Login sent and received by the module. The module does not say whether the code is correct: check in the function that needs the login.",
    "Luz de avaria":
        "Warning light",
    "Nenhuma centralina indicou o estado dos monitores de prontidão.":
        "No control unit reported the readiness monitor status.",
    "Nenhuma porta escolhida em Opções":
        "No port selected in Options",
    "Não foi possível abrir o cabo. Feche outros programas de diagnóstico que o possam estar a usar e confirme a porta do cabo em Opções.":
        "The cable could not be opened. Close other diagnostic programs that may be using it and check the cable port in Options.",
    "Não há ligação ao veículo: carregue em Ligar na página OBD — todas as marcas.":
        "Not connected to the vehicle: click Connect on the OBD — all makes page.",
    "O Auto-Scan foi interrompido ({scanned} de {total} controladores verificados): o resultado é parcial.":
        "The Auto-Scan was interrupted ({scanned} of {total} modules checked): the result is partial.",
    "O Auto-Scan parou porque o cabo deixou de responder (desligado do USB ou bloqueado). Os controladores já lidos ficaram guardados.\n\nDesligue o cabo do USB, volte a ligá-lo e repita o Auto-Scan.":
        "The Auto-Scan stopped because the cable stopped responding (unplugged from USB or blocked). The modules already read were saved.\n\nUnplug the cable from USB, plug it back in and repeat the Auto-Scan.",
    "O PC encontra o cabo.":
        "The PC finds the cable.",
    "O PC não encontra o cabo: volte a ligá-lo ao USB (ou experimente outra porta USB).":
        "The PC cannot find the cable: plug it back into USB (or try another USB port).",
    "O adaptador OBD está a responder.":
        "The OBD adapter is responding.",
    "O adaptador OBD já está ligado ao veículo.":
        "The OBD adapter is already connected to the vehicle.",
    "O adaptador ligou-se ao veículo, mas nenhuma centralina respondeu correctamente.":
        "The adapter connected to the vehicle, but no control unit answered correctly.",
    "O cabo deixou de responder ou não está disponível. Desligue o cabo do USB, volte a ligá-lo e tente de novo. Se continuar, crie um Pacote de suporte em Opções e envie-o.":
        "The cable stopped responding or is not available. Unplug the cable from USB, plug it back in and try again. If it continues, create a Support package in Options and send it.",
    "O cabo está a comunicar com o carro.":
        "The cable is communicating with the car.",
    "O cabo está a ser usado por outro programa. Feche os outros programas de diagnóstico e tente de novo.":
        "The cable is being used by another program. Close the other diagnostic programs and try again.",
    "O cabo está pronto e a comunicar com o carro.":
        "The cable is ready and communicating with the car.",
    "O cabo não está a comunicar com o carro. Confirme que está bem encaixado na ficha de diagnóstico e que a ignição está ligada, e tente de novo.":
        "The cable is not communicating with the car. Check that it is firmly plugged into the diagnostic socket and that the ignition is on, and try again.",
    "O cabo não está a comunicar com o carro. Confirme que está bem encaixado na ficha de diagnóstico e que a ignição está ligada.":
        "The cable is not communicating with the car. Check that it is firmly plugged into the diagnostic socket and that the ignition is on.",
    "O cabo não está a comunicar com o carro. Confirme que está bem encaixado na ficha de diagnóstico e que a ignição está ligada. Se continuar, este cabo pode não ser compatível: crie um Pacote de suporte em Opções e envie-o.":
        "The cable is not communicating with the car. Check that it is firmly plugged into the diagnostic socket and that the ignition is on. If it continues, this cable may not be compatible: create a Support package in Options and send it.",
    "O cabo vê a linha K do carro.":
        "The cable sees the car's K-line.",
    "O equipamento na porta {port_name} não é um adaptador OBD compatível.":
        "The equipment on port {port_name} is not a compatible OBD adapter.",
    "O módulo não respondeu. Confirme que a ignição está ligada e tente de novo.":
        "The module did not answer. Check that the ignition is on and try again.",
    "O módulo recusou o pedido.":
        "The module refused the request.",
    "O servidor de actualizações respondeu com o erro {code}.":
        "The update server answered with error {code}.",
    "O veículo não respondeu. Confirme que a ignição está ligada e que o veículo tem diagnóstico OBD.":
        "The vehicle did not answer. Check that the ignition is on and that the vehicle has OBD diagnostics.",
    "OBD — todas as marcas":
        "OBD — all makes",
    "Os dados vêm do simulador OBD, não de um veículo.":
        "The data comes from the OBD simulator, not from a vehicle.",
    "Porta do adaptador":
        "Adapter port",
    "Procurar (Ctrl+K): páginas, controladores, acções e avarias":
        "Search (Ctrl+K): pages, modules, actions and faults",
    "Resposta inesperada do servidor de actualizações.":
        "Unexpected answer from the update server.",
    "Sem cabo":
        "No cable",
    "Sem comunicação com este controlador.":
        "No communication with this module.",
    "Sem ligação à internet ou o servidor de actualizações não respondeu.":
        "No internet connection, or the update server did not answer.",
    "Sessão gravada por uma versão anterior, que não registava o equipamento: não se sabe se veio do simulador ou do carro.":
        "Session saved by an earlier version, which did not record the equipment: it is not known whether it came from the simulator or the car.",
    "Simulador OBD (todas as marcas) — experimentar sem carro":
        "OBD simulator (all makes) — try without a car",
    "Simulador OBD activo — os dados são fictícios":
        "OBD simulator active — the data is fictitious",
    "Simulador VAG — experimentar sem carro":
        "VAG simulator — try without a car",
    "Simulador — sem carro":
        "Simulator — no car",
    "Testar ligação":
        "Test connection",
    "Todas as marcas":
        "All makes",
    "VERSÃO {VERSION}":
        "VERSION {VERSION}",
    "VERSÃO {VERSION}  ·  DIAGNÓSTICO PROFISSIONAL":
        "VERSION {VERSION}  ·  PROFESSIONAL DIAGNOSTICS",
    "Verificar o cabo e a ligação ao carro":
        "Check the cable and the connection to the car",
    "Volte a instalar o Roots Auto Doctor e carregue outra vez em Detectar cabo.":
        "Reinstall Roots Auto Doctor and click Detect cable again.",
    "a iniciar…":
        "starting…",
    "medida pelo adaptador":
        "measured by the adapter",
    "o veículo não indicou o VIN":
        "the vehicle did not report the VIN",
    "sem nome":
        "unnamed",
    "{device} — Bluetooth":
        "{device} — Bluetooth",
    "{device} — Cabo USB":
        "{device} — USB cable",
    "{device} — Porta série":
        "{device} — Serial port",
    "{e}. Se continuar, crie um Pacote de suporte em Opções e envie-o.":
        "{e}. If it continues, create a Support package in Options and send it.",
    "{n} avaria(s) encontrada(s)":
        "{n} fault(s) found",
    "{v:.1f} V — baixa: bateria fraca, ignição desligada ou mau contacto na ficha":
        "{v:.1f} V — low: weak battery, ignition off or poor contact in the socket",
    "{v} centralina(s)":
        "{v} control unit(s)",
    "A versão nova já foi descarregada e verificada. Instala-se sozinha quando fechar o programa; os diagnósticos, a licença e as definições ficam guardados.":
        "The new version has already been downloaded and verified. It installs itself when you close the program; diagnostics, the licence and settings are kept.",
    "A versão {version} descarregada não passou na verificação de segurança e foi apagada.":
        "The downloaded version {version} failed the security check and was deleted.",
    "A versão {version} não tem instalador assinado: actualize à mão.":
        "Version {version} has no signed installer: update manually.",
    "Actualizado para a versão {version}":
        "Updated to version {version}",
    "Actualizar automaticamente (precisa de internet)":
        "Update automatically (needs internet)",
    "Ao abrir, o programa procura uma versão nova. Se houver, descarrega-a enquanto trabalha e instala-a quando o fechar; os diagnósticos, a licença e as definições ficam guardados. Na versão portátil só avisa. Sem internet não acontece nada.":
        "When it opens, the program looks for a new version. If there is one, it downloads it while you work and installs it when you close the program; diagnostics, the licence and settings are kept. The portable version only notifies. Without internet nothing happens.",
    "Instala-se sozinha quando fechar o programa.":
        "It installs itself when you close the program.",
    "Já tem a versão mais recente ({VERSION}).":
        "You already have the latest version ({VERSION}).",
    "Não foi possível descarregar a versão {version}.":
        "Version {version} could not be downloaded.",
    "Versão {version} descarregada: instala-se quando fechar o programa":
        "Version {version} downloaded: it installs when you close the program",
    "Versão {version} pronta":
        "Version {version} ready",
    "Adaptador ELM327 / OBDLink em modo CAN cru (ATCAF0)":
        "ELM327 / OBDLink adapter in raw CAN mode (ATCAF0)",
    "Adaptador OBD — VAG desde ~2004 e todas as marcas":
        "OBD adapter — VAG from ~2004 and all makes",
    "Cabo VAG — VW, Audi, Seat, Škoda até ~2005":
        "VAG cable — VW, Audi, Seat, Škoda up to ~2005",
    "Informação, avarias e valores de medição de cada módulo; adaptação e codificação nos modelos até ~2005.":
        "Information, faults and measuring values for each module; adaptation and coding on models up to ~2005.",
    "Ligue o cabo ao PC e carregue em Detectar cabo: o programa encontra-o e escolhe a porta sozinho. Depois, com o cabo no carro e a ignição ligada, carregue em Testar ligação.\n\nCabo VAG: para os VW, Audi, Seat e Škoda até ~2005. Adaptador OBD (USB ou Bluetooth): para os VAG de ~2004 em diante (Controladores e Auto-Scan) e para avarias e dados de qualquer marca na página OBD — todas as marcas. Para os VAG mais recentes recomenda-se um adaptador OBDLink.":
        "Plug the cable into the PC and click Detect cable: the program finds it and selects the port by itself. Then, with the cable in the car and the ignition on, click Test connection.\n\nVAG cable: for VW, Audi, Seat and Škoda up to ~2005. OBD adapter (USB or Bluetooth): for VAG from ~2004 onwards (Modules and Auto-Scan) and for faults and data of any make on the OBD — all makes page. For newer VAG cars an OBDLink adapter is recommended.",
    "O Simulador OBD só tem o diagnóstico de todas as marcas.\n\nPara experimentar os controladores e o Auto-Scan do Grupo VW, escolha em Opções o Simulador VAG ou o Simulador VAG por CAN.":
        "The OBD simulator only has all-makes diagnostics.\n\nTo try the VW Group modules and the Auto-Scan, choose the VAG simulator or the VAG CAN simulator in Options.",
    "O controlador {address:02X} deixou de responder":
        "Module {address:02X} stopped responding",
    "O controlador {address:02X} não respondeu":
        "Module {address:02X} did not answer",
    "O simulador OBD só tem o diagnóstico de todas as marcas. Para experimentar os controladores VAG, escolha em Opções o Simulador VAG ou o Simulador VAG por CAN.":
        "The OBD simulator only has all-makes diagnostics. To try the VAG modules, choose the VAG simulator or the VAG CAN simulator in Options.",
    "Simulador VAG por CAN (2004 em diante) — experimentar sem carro":
        "VAG CAN simulator (2004 onwards) — try without a car",
    "VW TP 2.0 + KWP2000 (CAN 500 kbit/s) — VAG ~2004 a ~2012":
        "VW TP 2.0 + KWP2000 (CAN 500 kbit/s) — VAG ~2004 to ~2012",
    # --- 1.11.0: gravação e validação no carro, KWP2000 (escrita), J2534 CAN, relatório e veículos
    " — {plate}":
        " — {plate}",
    "A codificação tem de estar entre 0000000 e 9999999":
        "The coding must be between 0000000 and 9999999",
    "A gravar a comunicação":
        "Recording the communication",
    "A gravar toda a comunicação com o carro. Repita o que falhou e depois carregue em Parar gravação.":
        "Recording all communication with the car. Repeat what failed and then click Stop recording.",
    "A identificação deste controlador não está no formato conhecido: a codificação e a adaptação ainda não estão disponíveis para ele.":
        "This module's identification is not in the known format: coding and adaptation are not available for it yet.",
    "A interface de diagnóstico está a responder.\n\nA ligação ao veículo faz-se na página OBD — todas as marcas, ou em Controladores e Auto-Scan para os VAG por CAN.":
        "The diagnostic interface is responding.\n\nConnect to the vehicle on the OBD — all makes page, or in Modules and Auto-Scan for VAG cars over CAN.",
    "A interface respondeu.":
        "The interface responded.",
    "A pré-visualização mostra o relatório tal como vai sair.":
        "The preview shows the report exactly as it will come out.",
    "A validar… não desligue o cabo nem a ignição.":
        "Validating… do not unplug the cable or switch the ignition off.",
    "A verificar…":
        "Checking…",
    "Abrir a interface":
        "Open the interface",
    "Abrir pasta das gravações":
        "Open recordings folder",
    "Abrir relatório":
        "Open report",
    "Avarias com o byte de estado":
        "Faults with the status byte",
    "Byte de estado":
        "Status byte",
    "Bytes: {what} (evento {event})":
        "Bytes: {what} (event {event})",
    "CAN cru 500 kbit/s: ISO-TP + OBD-II / UDS e VW TP 2.0 + KWP2000":
        "Raw CAN 500 kbit/s: ISO-TP + OBD-II / UDS and VW TP 2.0 + KWP2000",
    "Cabo e ignição":
        "Cable and ignition",
    "Cada carro fica registado uma vez, com o cliente e os dados da última visita.":
        "Each car is registered once, with the customer and the details of the last visit.",
    "Canal de adaptação inválido":
        "Invalid adaptation channel",
    "Centralina KWP2000: o significado do byte de estado ainda não está confirmado. Escreva ao lado de cada código o estado que o VCDS mostra (ex.: 35-10) — é isso que fecha esta dúvida.":
        "KWP2000 module: the meaning of the status byte is not confirmed yet. Write next to each code the status VCDS shows (e.g. 35-10) — that settles this question.",
    "Cliente conhecido · {n} visita(s) · última em {date}":
        "Known customer · {n} visit(s) · last on {date}",
    "Codificar o controlador com {v}?\nActual: {v2}":
        "Code the module with {v}?\nCurrent: {v2}",
    "Codificação inválida (0000000 a 9999999).":
        "Invalid coding (0000000 to 9999999).",
    "Codificação {coding}":
        "Coding {coding}",
    "Com o cabo no carro e a ignição ligada (motor parado), o programa liga ao motor, ao painel e ao ABS, lê a identificação, as avarias e o bloco 001, e grava toda a comunicação. No fim, compare as avarias com o VCDS e envie a gravação e o relatório.":
        "With the cable in the car and the ignition on (engine off), the program connects to the engine, the instrument cluster and the ABS, reads the identification, the faults and block 001, and records all the communication. At the end, compare the faults with VCDS and send the recording and the report.",
    "Com o equipamento \"Adaptador OBD\": página OBD — todas as marcas (os mesmos serviços OBD-II/UDS) e controladores VAG por CAN (TP2.0, os mesmos serviços de leitura)":
        "With the \"OBD adapter\" equipment: OBD — all makes page (the same OBD-II/UDS services) and VAG modules over CAN (TP2.0, the same reading services)",
    "Como o VCDS deve mostrar":
        "How VCDS should show it",
    "Compare cada linha com o VCDS no mesmo carro: o código e o estado (por exemplo 35-10) têm de ser iguais.":
        "Compare each line with VCDS on the same car: the code and the status (for example 35-10) must match.",
    "Código aceite: o controlador concedeu o acesso.":
        "Code accepted: the module granted access.",
    "Detalhe":
        "Detail",
    "Diagnósticos":
        "Diagnostics",
    "Enviar ao suporte":
        "Send to support",
    "Envie a gravação e este relatório ao suporte.":
        "Send the recording and this report to support.",
    "Erro novo em {cmd}: {msg}":
        "New error in {cmd}: {msg}",
    "Escolha um veículo da lista.":
        "Choose a vehicle from the list.",
    "Falhou":
        "Failed",
    "Ficaram {n} avaria(s) (provavelmente ainda presentes).":
        "{n} fault(s) remained (probably still present).",
    "Ficheiros":
        "Files",
    "Gravar comunicação":
        "Record communication",
    "Gravação":
        "Recording",
    "Gravação da comunicação: {path}":
        "Communication recording: {path}",
    "Gravação guardada":
        "Recording saved",
    "Gravação guardada: {path}\nEnvie-a com o Pacote de suporte.":
        "Recording saved: {path}\nSend it with the Support package.",
    "Gravação: {capture}\nRelatório: {report}":
        "Recording: {capture}\nReport: {report}",
    "Gravações (*.radrec)":
        "Recordings (*.radrec)",
    "Guardar PDF…":
        "Save PDF…",
    "Guardar página…":
        "Save web page…",
    "Identificação":
        "Identification",
    "Identificação, avarias, blocos de medição, codificação e adaptação (as mesmas do KWP2000 pela linha K)":
        "Identification, faults, measuring blocks, coding and adaptation (the same as KWP2000 over the K-line)",
    "Imprimir…":
        "Print…",
    "Iniciar validação":
        "Start validation",
    "Memória limpa.":
        "Memory cleared.",
    "Nenhuma avaria lida.":
        "No faults read.",
    "No fim, apagar as avarias do motor e voltar a ler (escreve no carro)":
        "At the end, clear the engine faults and read them again (writes to the car)",
    "Nova codificação (7 algarismos)":
        "New coding (7 digits)",
    "Não feito":
        "Not done",
    "Não foi possível abrir a gravação: {e}":
        "Could not open the recording: {e}",
    "Não foi possível ler a gravação {name}:\n{e}":
        "Could not read the recording {name}:\n{e}",
    "Não instalado":
        "Not fitted",
    "Não respondeu (o carro pode não ter este controlador).":
        "No answer (the car may not have this module).",
    "O controlador não tem o canal {ch:02d}.":
        "The module does not have channel {ch:02d}.",
    "O controlador pede o código de acesso: faça primeiro o Login (separador Login) e repita.":
        "The module asks for the access code: do the Login first (Login tab) and try again.",
    "O controlador recusou o código de acesso. Depois de várias tentativas erradas a centralina pode bloquear o acesso durante uns minutos: confirme o código antes de tentar outra vez.":
        "The module refused the access code. After several wrong attempts the module may lock access for a few minutes: check the code before trying again.",
    "O motor não comunicou: a validação não está completa.":
        "The engine did not communicate: the validation is not complete.",
    "O valor de adaptação tem de estar entre 0 e 65535":
        "The adaptation value must be between 0 and 65535",
    "Observações para o cliente":
        "Notes for the customer",
    "Opcional: trabalho feito, peças recomendadas, próxima revisão…":
        "Optional: work done, recommended parts, next service…",
    "Os veículos aparecem aqui depois do primeiro diagnóstico guardado.":
        "Vehicles appear here after the first saved diagnostic.",
    "PDF (*.pdf)":
        "PDF (*.pdf)",
    "Pacote de suporte guardado em:\n{path}\n\nEnvie este ficheiro ao suporte. Contém os registos dos últimos dias, as últimas gravações da comunicação e a informação do cabo; não contém dados de clientes.":
        "Support package saved to:\n{path}\n\nSend this file to support. It contains the logs of the last few days, the latest communication recordings and the cable information; it does not contain customer data.",
    "Para o cliente — linguagem simples":
        "For the customer — plain language",
    "Parar gravação":
        "Stop recording",
    "Passo":
        "Step",
    "Passos":
        "Steps",
    "Peça":
        "Part",
    "Procurar matrícula, VIN, cliente ou modelo":
        "Search plate, VIN, customer or model",
    "Página web (*.html)":
        "Web page (*.html)",
    "Quando algo não funcionar num carro: carregue em Gravar comunicação, repita o que falhou, pare a gravação e envie o Pacote de suporte (leva as últimas gravações).":
        "When something does not work on a car: click Record communication, repeat what failed, stop the recording and send the Support package (it includes the latest recordings).",
    "Relatório enviado para a impressora":
        "Report sent to the printer",
    "Relatório técnico":
        "Technical report",
    "Repetir validação":
        "Repeat validation",
    "Resultado":
        "Result",
    "Resultado diferente em {cmd}":
        "Different result in {cmd}",
    "Sem avarias.":
        "No faults.",
    "Sem resposta do cabo.":
        "No answer from the cable.",
    "Semente de segurança incompleta":
        "Incomplete security seed",
    "Software {v}":
        "Software {v}",
    "Suporte":
        "Support",
    "Testado só com a interface J2534 simulada. O ISO-TP e o TP2.0 são feitos pelo programa sobre o canal CAN cru (não usa o ISO15765 do driver). Na versão compilada a interface J2534 simulada só imita a linha K.":
        "Tested only with the simulated J2534 interface. ISO-TP and TP2.0 are done by the program over the raw CAN channel (the driver's ISO15765 is not used). In the compiled version the simulated J2534 interface only imitates the K-line.",
    "Testado só com o simulador J2534. KW1281 é recusado (a norma J2534 não permite os tempos por byte).":
        "Tested only with the J2534 simulator. KW1281 is refused (the J2534 standard does not allow per-byte timing).",
    "Todos os Auto-Scans e relatórios ficam guardados neste computador. Procure pela matrícula, pelo VIN ou pelo nome do cliente.":
        "Every Auto-Scan and report is kept on this computer. Search by number plate, VIN or customer name.",
    "Todos os passos feitos passaram. Compare as avarias com o VCDS e envie a gravação.":
        "Every step that ran passed. Compare the faults with VCDS and send the recording.",
    "Técnico":
        "Technician",
    "Técnico — protocolos, codificação e estado das avarias":
        "Technical — protocols, coding and fault status",
    "Usar no diagnóstico":
        "Use in diagnostic",
    "Validação interrompida.":
        "Validation stopped.",
    "Validação no carro":
        "On-car validation",
    "Valores recebidos.":
        "Values received.",
    "Ver diagnósticos":
        "Show diagnostics",
    "Verificar gravação":
        "Check recording",
    "Verificar gravação…":
        "Check recording…",
    "Veículo {plate} pronto para o diagnóstico":
        "Vehicle {plate} ready for the diagnostic",
    "Veículos":
        "Vehicles",
    "Visitas":
        "Visits",
    "estado 0x{v:02X}":
        "status 0x{v:02X}",
    "interface pronta":
        "interface ready",
    "tipo {n:02d}":
        "type {n:02d}",
    "{addr:02X} {name}: ligar":
        "{addr:02X} {name}: connect",
    "{name}: há diferenças em relação à gravação.":
        "{name}: there are differences from the recording.",
    "{name}: o programa actual repete a gravação sem diferenças ({commands} comandos, {results} resultados).":
        "{name}: the current program repeats the recording with no differences ({commands} commands, {results} results).",
    "{n} avaria(s): {codes}":
        "{n} fault(s): {codes}",
    "{n} passo(s) falharam: veja o detalhe e envie a gravação.":
        "{n} step(s) failed: see the detail and send the recording.",
    "{prefix}: apagar avarias e voltar a ler":
        "{prefix}: clear faults and read again",
    "{prefix}: bloco de medição 001 ({n} leituras)":
        "{prefix}: measuring block 001 ({n} readings)",
    "{prefix}: ler avarias":
        "{prefix}: read faults",
    "{prefix}: ligar":
        "{prefix}: connect",
    "{prefix}: ligar e identificar":
        "{prefix}: connect and identify",
    "Última visita":
        "Last visit",
    "Sensor de pressão do turbo A — sinal baixo":
        "Turbocharger boost sensor A — circuit low",
    "Sensor de pressão do turbo A — sinal alto":
        "Turbocharger boost sensor A — circuit high",
    "Recirculação de gases de escape (EGR) — gama/funcionamento do circuito":
        "Exhaust gas recirculation (EGR) — circuit range/performance",
    "Sensor A da recirculação de gases de escape (EGR) — sinal baixo":
        "Exhaust gas recirculation (EGR) sensor A — circuit low",
    "Sensor A da recirculação de gases de escape (EGR) — sinal alto":
        "Exhaust gas recirculation (EGR) sensor A — circuit high",
    "Sistema EVAP — caudal de purga incorrecto":
        "EVAP system — incorrect purge flow",
    "O controlador não tem ajuste básico no grupo {group:03d}.":
        "The module has no basic setting in group {group:03d}.",
    "Canal TP2.0 (abertura, parâmetros, ACK, teste do canal, fecho), identificação, avarias (ler/apagar), blocos de medição; Auto-Scan pelos endereços VAG; codificação, adaptação, acesso de segurança, ajustes básicos e saídas (os mesmos pedidos do KWP2000 pela linha K)":
        "TP2.0 channel (setup, parameters, ACK, channel test, disconnect), identification, faults (read/clear), measuring blocks; Auto-Scan through the VAG addresses; coding, adaptation, security access, basic settings and output tests (the same requests as KWP2000 over the K-line)",
    "Escrita baseada nas capturas de uma EDC16 publicadas pelo kw1281test; só disponível quando a identificação tem o formato conhecido. Byte de estado das avarias descodificado com a tabela KW1281 — por confirmar num carro (a validação no carro mostra o byte cru).":
        "Writing based on the EDC16 captures published by kw1281test; only available when the identification has the known format. Fault status byte decoded with the KW1281 table — to be confirmed on a car (the on-car validation shows the raw byte).",
    "Identificação (com codificação e código de oficina), avarias (ler/apagar), blocos de medição, codificação (3B 9A, com releitura), adaptação (ler/testar/gravar, com releitura), acesso de segurança (27 03/04), ajustes básicos (31 B8/BA 00 + grupo), teste de saídas (31 B8/B9/BA 01 02)":
        "Identification (with coding and workshop code), faults (read/clear), measuring blocks, coding (3B 9A, read back), adaptation (read/test/save, read back), security access (27 03/04), basic settings (31 B8/BA 00 + group), output tests (31 B8/B9/BA 01 02)",
    "Sem validação num carro nem num adaptador físico. A escrita só é oferecida quando a identificação tem o formato conhecido e cada valor gravado é lido outra vez. Os ELM327 baratos podem ser lentos para os ACK do TP2.0; recomenda-se OBDLink.":
        "No validation on a car or with a physical adapter. Writing is only offered when the identification has the known format, and every saved value is read back. Cheap ELM327 adapters may be too slow for the TP2.0 ACKs; OBDLink is recommended.",
}
