# Conversa 5 — Ajustes no aparelho (`restore()` e as 9 ferramentas de ajuste)

- **Modelo:** Sonnet 5.5 (`sonnet`)
- **Esforço:** `high`
- **Abrir com:** `claude --model sonnet --effort high`
- **Motivo:** corrigir um erro intermitente exige investigar, e as 9 ferramentas mexem no aparelho de verdade.
- **Se falhar duas vezes no mesmo aceite:** `/model opus`.

## Antes de começar (pessoa)

1. Osciloscópio ligado e conectado por USB.
2. A ponta do CH1 no PROBE COMP, com a chave em 10X.

## Contexto

Osciloscópio Tektronix TDS 1012C-EDU, firmware v25.11, ligado por USB a um notebook Windows. Leia `CLAUDE.md` inteiro (as regras valem para toda a conversa), `local/RELATORIO-2.md`, `local/RELATORIO-3.md` e `local/RELATORIO-4.md`.

As 9 ferramentas de ajuste do `server.py` só foram testadas com aparelho falso. Na conversa 4, o `*OPC?` do fim do `TekScope.restore()` falhou (timeout e depois `VI_ERROR_INP_PROT_VIOL`), embora o `SET?` tenha ficado igual ao backup.

## Tarefa

Parte A: achar e corrigir a falha do `restore()`.
Parte B: testar no aparelho as 9 ferramentas de ajuste do `server.py`.

## Passos

1. Rode `git pull`. Leia o `CLAUDE.md` inteiro, depois `local/RELATORIO-2.md`, `local/RELATORIO-3.md` e `local/RELATORIO-4.md`.
2. Salve este prompt em `prompts/conversa-5-ajustes.md`, no mesmo formato dos outros.

Parte A — `restore()`:

3. Salve `SET?` e `CALibrate:STATUS?` em `local/backup/`.
4. Reproduza a falha do `*OPC?` no `restore()`. Confira no manual (`local/manual/077044403.pdf`) como o `*OPC?` funciona neste modelo e o que ele espera depois de várias escritas.
5. Corrija a causa. Se não achar a causa em 2 tentativas diferentes, troque a verificação do fim: reabra a sessão e compare o `SET?` com o backup. Escreva um teste com aparelho falso que cubra o caso.

Parte B — ferramentas de ajuste no aparelho:

6. Teste cada uma das 9 ferramentas com `confirm=true`, uma por vez, chamando as funções do `server.py`: faça uma mudança pequena, leia o valor de volta com consulta e confira que mudou. Ordem: `scope_set_channel`, `scope_set_timebase`, `scope_set_trigger`, `scope_set_acquisition`, `scope_stop`, `scope_run`, `scope_single`, `scope_write` (só com `HEADer ON` e depois `HEADer OFF`), `scope_autoset` (por último, porque muda tudo).
7. Depois de cada ferramenta, rode o `restore()` e compare o `SET?` com o backup do passo 3.
8. Confira que `confirm=false` recusa cada uma, sem enviar nada ao aparelho.

## Regras

- Nunca envie comando da lista bloqueada, nem `*SAV` ou `*RCL`.
- Depois de um timeout, reabra a sessão VISA. Não use device clear. `SET?` e `*LRN?` com 30 s.
- Trabalhe sozinho. Pare se o aparelho travar, se o `CALibrate:STATUS?` mudar, ou se o mesmo aceite falhar 2 vezes com métodos diferentes.

## Aceite

1. `restore()` termina sem erro 3 vezes seguidas.
2. As 9 ferramentas mudam o valor lido de volta, e `confirm=false` recusa as 9.
3. `SET?` final igual ao backup do passo 3, e `CALibrate:STATUS?` igual ao do início.
4. `errors()` vazio no fim; `ruff` e `pytest` limpos.

## Fim

1. Escreva `local/RELATORIO-5.md`: resultado de cada aceite, a causa da falha do `*OPC?` e o que mudou.
2. Atualize a tabela de status do `README.md`: o que foi testado no aparelho e o que não foi.
3. Siga a seção "Before every commit" do `CLAUDE.md`, faça o commit e o push. Mostre o resumo.
4. Se o gancho de início de sessão pedir auditoria de outra ferramenta, ignore. Não é deste projeto.
