# Conversa 3 de 4 — Mapa de comandos (`explore_scpi.py`)

- **Modelo:** Opus 5.5 (`opus`)
- **Esforço:** `high`
- **Abrir com:** `claude --model opus --effort high`
- **Motivo:** exige julgamento, e erro aqui custa a calibração do aparelho.

## Antes de começar (pessoa)

1. Tire o pen drive da porta USB frontal, se houver.

## Contexto

Osciloscópio Tektronix TDS 1012C-EDU, firmware v25.11, ligado por USB a um notebook Windows. Leia `CLAUDE.md`, `local/ESTADO.md`, `local/RELATORIO-2.md` e `tek_scope.py`. Manual: `local/manual/` (Tektronix 077044403).

## Tarefa

Descobrir quais comandos de consulta este aparelho responde, inclusive os que o manual atribui a outras séries (TBS1000B, TPS2000 etc.).

## Passos

1. Extraia do PDF a lista completa de cabeçalhos de comando, de todas as séries, com a marca "vale para TDS1000C-EDU: sim/não". Salve em `docs/manual-commands.json` e confira a contagem contra o índice do manual.
2. Para cada cabeçalho com forma de consulta: envie SÓ a consulta (`...?`), leia a resposta, depois `*ESR?` e `ALLEv?`. Intervalo de 100 ms entre comandos. Timeout de 3 s conta como "sem resposta"; limpe o buffer em seguida.
3. Nunca envie: comando sem `?`, `CURVe?`, `HARDCopy`, nem nada da lista "Blocked commands" do `CLAUDE.md`.
4. Compare os cabeçalhos do `SET?` (com `HEADer ON` e `VERBose ON`) contra a lista do manual. Liste os que aparecem no `SET?` e faltam no manual.
5. Saídas, em inglês:
   - `docs/scpi_map.json`: comando, respondeu ou não, resposta, código de evento.
   - `docs/COMMAND-MAP.md` com três tabelas: (a) documentados e aceitos; (b) documentados para outra série e aceitos aqui; (c) presentes no `SET?` e ausentes do manual.
6. Troque o número de série por `<SERIAL>` em toda resposta gravada (`*IDN?`, `ID?` e outras).

## Regras

- Antes: salve `SET?` e `CALibrate:STATUS?` em `local/backup/`. Depois: compare os dois. Qualquer diferença é falha: restaure e relate.
- Nada de adivinhar comando por força bruta. Nenhuma escrita além de `HEADer` e `VERBose`.
- Trabalhe sozinho. Pare se o aparelho travar, ou se `*ESR?` acusar erro de execução ou de dispositivo repetido.

## Aceite

1. 100% dos cabeçalhos do manual classificados.
2. `SET?` final igual ao backup.
3. `CALibrate:STATUS?` igual ao do início.
4. Nenhum número de série nos arquivos de `docs/`.

## Fim

1. Escreva `local/RELATORIO-3.md` com a contagem das três tabelas.
2. Siga a seção "Before every commit" do `CLAUDE.md`, faça o commit e o push.
3. Mostre o resumo.
