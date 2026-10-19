# Clone HEX-USB (VID 0403 / PID FA24) no Roots Auto Doctor

## O que é este cabo (medido neste PC a 2026-10-19)

| Campo | Valor | Fonte |
|---|---|---|
| Nome USB | `Ross-Tech HEX-USB` (sem driver) / `Ross-Tech Direct USB Interface` (com driver) | `Get-PnpDevice` |
| VID / PID | `0403` / `FA24` | HardwareID |
| bcdDevice | `0600` → chip **FTDI FT232R** | HardwareID `REV_0600` |
| N.º de série | `RT000001` | InstanceId |
| Classe USB | `FF/FF/FF` (vendor-specific, típica dos FTDI) | CompatibleID |
| Driver actual | serviço `RT-USB`, `oem28.inf`, Ross-Tech 2.10.0.0 (2014), **não assinado** | `Win32_PnPSignedDriver` |
| DLL do driver | `C:\Windows\System32\RT-USB.DLL` — **32 bits**, exporta a API D2XX da FTDI (`FT_OpenEx`, `FT_SetBaudRate`, `FT_SetBreakOn`…) | cabeçalho PE + tabela de exportações |

Apesar do nome "HEX-V2", o cabo identifica-se como **HEX-USB** (o produto antigo) e é um FT232R com o PID
da Ross-Tech. Não é uma HEX-V2: não há CAN acessível por este caminho.

**Ainda não se sabe:** se o FT232R está ligado directamente ao transceptor da linha K (cabo "dumb") ou se há
um microcontrolador pelo meio. Só o teste de eco com o carro o diz (passo 3 em baixo).

## Como o programa fala com ele

O chip FTDI comporta-se como uma UART. O Roots Auto Doctor usa-o como um cabo KKL: o mesmo `KLine`
(init a 5 baud por BREAK, KW1281, KWP2000), só muda a forma de chegar à UART.

| Porta na lista | Módulo | Driver necessário | Notas |
|---|---|---|---|
| `D2XX:RT000001` | `rad/d2xx.py` + `rad/d2xx_bridge.py` | RT-USB (o que já está instalado) | O `RT-USB.DLL` é de 32 bits → precisa de um **Python 3 de 32 bits** instalado ao lado. O VCDS continua a funcionar. |
| `FTDI:0403:FA24:RT000001` | `rad/ftdi_direct.py` (pyftdi + libusb) | **WinUSB** (Zadig) | Corre no próprio processo, latência 1 ms. O VCDS deixa de reconhecer o cabo enquanto tiver WinUSB. |

Só são usados pedidos normais do chip FTDI (velocidade, 8N1, BREAK, DTR/RTS, latência, purge, read/write).
Não há comandos proprietários da Ross-Tech, nem escrita na EEPROM, nem alteração de firmware.

## Instalação

```powershell
cd $env:USERPROFILE\Desktop\RootsAutoDoctor
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Opção A — manter o driver RT-USB (D2XX)

1. Instalar o Python 3 de 32 bits ao lado do actual (não substitui o de 64 bits):
   ```powershell
   winget install --id Python.Python.3.13 --architecture x86
   py -0p        # deve aparecer -V:3.13-32
   ```
2. Opções → **Detectar cabo** → deve dizer "pronta pelo driver RT-USB" e escolher `D2XX:RT000001`.

Se o `RT-USB.DLL` estiver noutro sítio: `$env:RAD_D2XX_DLL = "C:\caminho\RT-USB.DLL"`.

### Opção B — WinUSB (acesso USB directo)

1. Descarregar o Zadig de https://zadig.akeo.ie/ (página oficial).
2. Options → List All Devices → escolher **Ross-Tech Direct USB Interface** (USB ID `0403 FA24`).
3. Driver de destino **WinUSB** → *Replace Driver*.
4. Opções → **Detectar cabo** → deve dizer "pronta por USB directo" e escolher `FTDI:0403:FA24:RT000001`.

Para voltar ao driver da Ross-Tech: Gestor de Dispositivos → o dispositivo → Controlador → *Reverter
controlador* (ou desinstalar e voltar a ligar o cabo).

### Verificar o driver

```powershell
Get-PnpDevice -PresentOnly | Where-Object InstanceId -match 'VID_0403&PID_FA24' | Format-List Status,Service,FriendlyName,InstanceId
```

`Service` = `RT-USB` (opção A) ou `WinUSB` (opção B); `Status` = `OK`.

## Testes com o hardware

A sonda `tools\hex_probe.py` faz os passos em linha de comandos e mostra tudo o que acontece. Os mesmos
passos 3–5 estão na aplicação em Opções → **Diagnóstico da ligação**.

| # | Passo | Comando | Precisa de carro | Resultado esperado |
|---|---|---|---|---|
| 1 | Detecção USB | `.venv\Scripts\python.exe tools\hex_probe.py` | não | VID/PID, chip FT232R, driver e porta proposta |
| 2 | Abrir o interface | `... tools\hex_probe.py --port D2XX:RT000001` | não | "aberta em N ms" + tipo/série lidos pelo D2XX |
| 3 | Eco da linha K | `... --port D2XX:RT000001 --echo` | **sim, ignição ON** | "OK — o cabo vê a linha K" |
| 4 | Identificação | `... --port D2XX:RT000001 --ecu 01` | sim | protocolo, velocidade, referência, codificação |
| 5 | Avarias + grupo 1 | (incluído no passo 4) | sim | lista de avarias e 4 valores do grupo 1 |

Experimentar pelo menos `01` (motor), `17` (painel) e `03` (ABS). Com a opção B, trocar a porta por
`FTDI:0403:FA24:RT000001`.

**Se o passo 3 falhar com a ignição ligada** (sem eco), a interface tem um microcontrolador entre o FTDI e a
ficha OBD e **não pode ser usada como cabo KKL**. Isso não se contorna sem o protocolo proprietário do
firmware, que não está documentado. Alternativas: cabo KKL 409.1 (FTDI/CH340) para carros com linha K, ou uma
interface J2534 com ISO 15765 para carros CAN.

## Estado da verificação

| O quê | Estado |
|---|---|
| Identificação USB (VID/PID, chip, série, driver) | **Verificado no hardware** |
| Detecção na aplicação (`Detectar cabo`, lista de portas `D2XX:RT000001`) | **Verificado no hardware** |
| Abrir o chip pelo D2XX | Não verificado — falta o Python de 32 bits |
| Abrir o chip por WinUSB | Não verificado — o driver actual é o RT-USB |
| Eco da linha K, init 5 baud, KW1281/KWP2000 com centralina real | Não verificado — precisa do carro |
| KLine + KW1281 sobre `FtdiSerial` (init 5 baud descodificado pelos tempos do BREAK) | Testado com chip simulado |
| KLine + KW1281/KWP2000 sobre a ponte D2XX (processo à parte) | Testado com backend simulado |

## Protocolos

| Camada | Este cabo (se for "dumb") | Notas |
|---|---|---|
| USB ↔ PC | FTDI (D2XX ou WinUSB/libusb) | transporte, não é protocolo de diagnóstico |
| Linha K, init 5 baud | sim | ISO 9141-2 / ISO 14230 físico |
| KW1281 | sim | precisa de confirmar cada byte — funciona por UART, não por J2534 |
| KWP2000 (ISO 14230) sobre linha K | sim (só leitura nesta versão: identificação, avarias, grupos) | |
| CAN / ISO-TP (ISO 15765) / UDS (ISO 14229) | **não** | o FT232R não tem CAN. Só com uma interface J2534 que declare ISO15765 — não implementado nesta versão |
