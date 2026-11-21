# Conversa 2 de 4 — Biblioteca de controle `tek_scope.py`

- **Modelo:** Sonnet 5.5 (`sonnet`)
- **Esforço:** `medium`
- **Abrir com:** `claude --model sonnet --effort medium`
- **Motivo:** a tarefa está toda especificada.
- **Se falhar duas vezes no mesmo aceite:** `/model opus`.

## Antes de começar (pessoa)

1. Ligue a ponta de prova do CH1 no terminal PROBE COMP (~5 V, 1 kHz).
2. Ponha a chave da ponta em 10X.

## Contexto

Osciloscópio Tektronix TDS 1012C-EDU, firmware v25.11, ligado por USB a um notebook Windows. A conexão já funciona. Leia `CLAUDE.md`, `local/ESTADO.md` e `local/RELATORIO-1.md` antes de tudo.

Referência obrigatória: *Digital Oscilloscope Series Programmer Manual*, Tektronix 077044403. Baixe o PDF para `local/manual/` e confira nele a sintaxe de CADA comando antes de usar. Se o manual divergir deste prompt, vale o manual; anote a divergência.

## Tarefa

Escrever `tek_scope.py` (classe `TekScope`) e os testes.

## Funções

1. Base: `connect()`, `close()`, `idn()`, `query(cmd)`, `write(cmd)`, `errors()` (lê `*ESR?` e `ALLEv?`), `state()` (`SET?`). Uma conexão por vez (arquivo de trava). Timeout de 10 s; 30 s para tela e forma de onda.
2. Canais: ler e ajustar `CH<x>:SCAle`, `POSition`, `COUPling`, `PRObe`, `BANdwidth`, `INVert`.
3. Horizontal: `HORizontal:MAIn:SCAle` e `HORizontal:MAIn:POSition`.
4. Trigger de borda: `TRIGger:MAIn:EDGE:SOUrce`, `:SLOpe`, `:COUPling`; `TRIGger:MAIn:LEVel`; `TRIGger:MAIn:MODe`; `TRIGger:STATE?`.
5. Aquisição: `ACQuire:STATE`, `ACQuire:STOPAfter`, `ACQuire:MODe`, `ACQuire:NUMAVg`; `run()`, `stop()`, `single()` com espera por `*OPC?`.
6. `autoset()`: `AUTOSet EXECute`.
7. Medidas: `MEASUrement:IMMed:SOUrce`, `:TYPe`, `:VALue?`, `:UNIts?`; `measure(tipo, canal)`.
8. Forma de onda: `DATa:SOUrce`, `DATa:ENCdg RIBinary`, `DATa:WIDth 1`, `DATa:STARt 1`, `DATa:STOP 2500`, `WFMPre?`, `CURVe?`. Conversão:
   - `tempo[n] = XZEro + XINcr * (n - PT_Off)`
   - `volts[n] = YZEro + YMUlt * (amostra[n] - YOFf)`
   - `waveform(canal)` devolve tempo, volts e o preâmbulo; `save_csv(caminho)`.
9. Tela: `HARDCopy:PORT USB`, `HARDCopy:FORMat BMP`, `HARDCopy STARt`, leitura do bloco bruto; `screenshot(caminho)` salva PNG. Se o manual indicar outro caminho para a porta USB traseira, siga o manual.
10. Bloqueio fixo dentro de `write()` e `query()`: a lista "Blocked commands" do `CLAUDE.md`. Só passa com `allow_dangerous=True` na chamada. Registre toda escrita em `local/logs/escritas.log`.

## Regras

- Antes de qualquer teste que mude ajustes: salve `SET?` em `local/backup/` e restaure no fim.
- Trabalhe sozinho. Pare só em falha depois de 2 tentativas diferentes, ou se precisar de comando da lista bloqueada.
- Código, comentários e documentos públicos em inglês.

## Aceite

Sinal PROBE COMP no CH1, ponta em 10X, `CH1:PRObe 10`.

1. `measure("FREQuency", 1)` entre 950 e 1050 Hz.
2. `measure("PK2pk", 1)` entre 4,5 e 5,5 V.
3. `waveform(1)` devolve 2500 pontos; gere `docs/ch1.png` (gráfico) e `docs/ch1.csv`.
4. `screenshot()` gera `docs/screen.png` legível.
5. `errors()` vazio no fim.
6. `SET?` final igual ao do backup.

## Fim

1. Escreva `local/RELATORIO-2.md`: resultado de cada aceite e divergências do manual.
2. Siga a seção "Before every commit" do `CLAUDE.md`, faça o commit e o push.
3. Mostre o resumo.
