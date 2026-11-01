# Novidades

O que muda em cada versão, escrito para os clientes. O programa mostra estas linhas antes de actualizar, no idioma
da interface (`### pt` e `### en`). Linguagem simples, sem nomes técnicos (cabos, protocolos, ficheiros).

Ao publicar uma versão, `tools/finish_build.py notes <versão>` junta a secção dessa versão ao texto da Release.
Uma versão sem secção aqui é publicada sem novidades (o programa só diz que há uma versão nova).

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
