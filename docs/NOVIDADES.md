# Novidades

O que muda em cada versão, escrito para os clientes. O programa mostra estas linhas antes de actualizar, no idioma
da interface (`### pt` e `### en`). Linguagem simples, sem nomes técnicos (cabos, protocolos, ficheiros).

Ao publicar uma versão, `tools/finish_build.py notes <versão>` junta a secção dessa versão ao texto da Release.
Uma versão sem secção aqui é publicada sem novidades (o programa só diz que há uma versão nova).

## 1.18.0

### pt
- Novo logótipo: o "R" de Roots com o ponteiro de um conta-rotações na zona vermelha. Lê-se bem mesmo em
  pequeno, na barra de tarefas.

### en
- New logo: the "R" of Roots with the needle of a rev counter in the red zone. It reads well even when small, on
  the taskbar.

## 1.17.0

### pt
- Nova página Início, mais simples: o estado do cabo e do carro logo no topo, com o botão para começar o
  Auto-Scan.
- A matrícula do carro em diagnóstico aparece em destaque, e os últimos veículos mostram logo, a cores, se tinham
  avarias.

### en
- New, simpler Home page: the cable and car status right at the top, with the button to start the Auto-Scan.
- The number plate of the car being diagnosed stands out, and the latest vehicles show at a glance, in colour,
  whether they had faults.

## 1.16.2

### pt
- Os valores com casas decimais aparecem com vírgula (por exemplo 12,4 V), como é habitual em Portugal.
- Mostradores mais limpos: os números da escala já não ficam por cima do valor.
- Caixas de números com setas visíveis e mais fáceis de ler.
- Na lista de avarias, o assistente de diagnóstico tem mais espaço e lê-se melhor.

### en
- Clearer gauges: the scale numbers no longer overlap the value.
- Number boxes with visible arrows and easier to read.
- In the fault list, the diagnostic assistant has more room and is easier to read.

## 1.16.1

### pt
- Ligação mais estável durante a leitura de valores, mesmo com o computador ocupado a desenhar os gráficos.
- O computador já não entra em suspensão a meio de uma ligação ao carro (por exemplo, num portátil a bateria
  durante um Auto-Scan).
- Se o programa fechar sozinho, fica um registo que permite perceber porquê.

### en
- More stable connection while reading measuring values, even when the computer is busy drawing the charts.
- The computer no longer goes to sleep in the middle of a connection to the car (for example, a laptop on battery
  during an Auto-Scan).
- If the program closes by itself, a log is left that makes it possible to find out why.

## 1.16.0

### pt
- Ligação mais estável aos controladores mais antigos: o programa dá-lhes o tempo de que precisam entre cada
  pedido, e a comunicação deixa de cair a meio.
- Se um controlador responder mas a ligação não arrancar à primeira, o programa espera um momento e tenta outra vez
  sozinho — também no Auto-Scan.
- Arranque da ligação mais seguro depois de um erro ou de mexer no cabo.
- Voltar a abrir um controlador é mais rápido: o programa lembra-se de como falou com ele da última vez.

### en
- More stable connection to older controllers: the program gives them the time they need between requests, and the
  communication no longer drops halfway.
- If a controller answers but the connection does not start the first time, the program waits a moment and tries
  again by itself — in Auto-Scan too.
- Safer start of the connection after an error or after the cable has been moved.
- Opening a controller again is faster: the program remembers how it talked to it the last time.

## 1.15.1

### pt
- Mensagens sobre o cabo mais simples e claras.

### en
- Simpler, clearer messages about the cable.

## 1.15.0

### pt
- Ligação mais rápida e mais segura aos controladores antigos que comunicam a outras velocidades (painéis, airbags,
  alguns ABS e rádios): o programa percebe logo à primeira tentativa qual é a velocidade certa.
- Se a ligação a um controlador falhar logo a seguir ao arranque, o programa tenta sozinho outra vez antes de
  desistir.

### en
- Faster and more reliable connection to older controllers that talk at other speeds (instrument clusters, airbags,
  some ABS units and radios): the program works out the right speed from the first attempt.
- If the connection to a controller fails right after it starts, the program tries again by itself before giving
  up.

## 1.14.2

### pt
- Novo "Ver gravações": veja os valores gravados em gráfico, com mínimo, máximo e média, e compare duas gravações
  (por exemplo, antes e depois de uma reparação).
- Enquanto lê os valores do motor, o programa avisa logo quando algo sai do normal: pressão do turbo, massa de ar,
  injectores, temperatura do motor ou tensão da bateria.
- As gravações ficam guardadas com o carro: na visita seguinte o programa compara sozinho com a anterior.
- O relatório passa a mostrar os valores lidos e os avisos que apareceram; o relatório técnico compara com a
  visita anterior.
- A actualização automática da versão portátil passa a esperar sempre que o programa feche antes de trocar os
  ficheiros.

### en
- New "View recordings": see the recorded values on a chart, with minimum, maximum and average, and compare two
  recordings (for example, before and after a repair).
- While reading the engine values, the program warns you straight away when something is out of the ordinary: boost
  pressure, air mass, injectors, engine temperature or battery voltage.
- Recordings are kept with the car: on the next visit the program compares with the previous one by itself.
- The report now shows the values read and the warnings that appeared; the technical report compares with the
  previous visit.
- The automatic update of the portable version now always waits for the program to close before replacing the
  files.

## 1.14.1

### pt
- Novo "Ver gravações": veja os valores gravados em gráfico, com mínimo, máximo e média, e compare duas gravações
  (por exemplo, antes e depois de uma reparação).
- Enquanto lê os valores do motor, o programa avisa logo quando algo sai do normal: pressão do turbo, massa de ar,
  injectores, temperatura do motor ou tensão da bateria.
- As gravações ficam guardadas com o carro: na visita seguinte o programa compara sozinho com a anterior.
- O relatório passa a mostrar os valores lidos e os avisos que apareceram; o relatório técnico compara com a
  visita anterior.

### en
- New "View recordings": see the recorded values on a chart, with minimum, maximum and average, and compare two
  recordings (for example, before and after a repair).
- While reading the engine values, the program warns you straight away when something is out of the ordinary: boost
  pressure, air mass, injectors, engine temperature or battery voltage.
- Recordings are kept with the car: on the next visit the program compares with the previous one by itself.
- The report now shows the values read and the warnings that appeared; the technical report compares with the
  previous visit.

## 1.14.0

### pt
- Novo "Ver gravações": veja os valores gravados em gráfico, com mínimo, máximo e média, e compare duas gravações
  (por exemplo, antes e depois de uma reparação).
- Enquanto lê os valores do motor, o programa avisa logo quando algo sai do normal: pressão do turbo, massa de ar,
  injectores, temperatura do motor ou tensão da bateria.
- As gravações ficam guardadas com o carro: na visita seguinte o programa compara sozinho com a anterior.
- O relatório passa a mostrar os valores lidos e os avisos que apareceram; o relatório técnico compara com a
  visita anterior.

### en
- New "View recordings": see the recorded values on a chart, with minimum, maximum and average, and compare two
  recordings (for example, before and after a repair).
- While reading the engine values, the program warns you straight away when something is out of the ordinary: boost
  pressure, air mass, injectors, engine temperature or battery voltage.
- Recordings are kept with the car: on the next visit the program compares with the previous one by itself.
- The report now shows the values read and the warnings that appeared; the technical report compares with the
  previous visit.

## 1.13.0

### pt
- O programa actualiza-se sempre sozinho, também na versão portátil: não precisa de fazer nada.
- Antes de actualizar, o programa mostra o que há de novo.
- Se uma actualização não terminar, o programa continua a funcionar na versão anterior e avisa.
- Se uma versão nova não abrir no seu computador, o programa volta sozinho à versão anterior.
- O pacote de suporte tira os números de chassis e as matrículas dos registos e leva mais informação para
  resolver problemas mais depressa.

### en
- The program always updates itself, also in the portable version: there is nothing to do.
- Before updating, the program shows what is new.
- If an update does not finish, the program keeps working on the previous version and tells you.
- If a new version does not open on your computer, the program goes back to the previous version by itself.
- The support package removes chassis numbers and number plates from the logs and includes more information to
  solve problems faster.

## 1.12.1

### pt
- As actualizações passam a instalar-se sozinhas.
- Novo botão "Actualizar agora": instala a versão nova e volta a abrir o programa.

### en
- Updates now install by themselves.
- New "Update now" button: installs the new version and opens the program again.
