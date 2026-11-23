# Conversa 6 — Quedas da USB e proteção das 4 ferramentas de execução

- **Modelo:** Sonnet 5.5 (`sonnet`)
- **Esforço:** `high`
- **Abrir com:** `claude --model sonnet --effort high`
- **Motivo:** mexe em configuração do Windows (energia) e em 4 ferramentas que enviam comando ao aparelho de verdade.
- **Se falhar duas vezes no mesmo aceite:** `/model opus`.

## Antes de começar (pessoa)

1. Osciloscópio ligado e conectado por USB, direto no notebook (sem hub).
2. A ponta do CH1 no PROBE COMP, com a chave em 10X.

## Contexto

Osciloscópio Tektronix TDS 1012C-EDU, firmware v25.11, ligado por USB a um notebook Windows. Leia `CLAUDE.md` inteiro (as regras valem para toda a conversa) e `local/RELATORIO-5.md`.

Na conversa 5, o aparelho saiu do barramento USB sozinho por alguns segundos, várias vezes. O `restore()` passou a se verificar e se repetir. `scope_run`, `scope_stop`, `scope_single` e `scope_autoset` ainda terminam com `*OPC?` na mesma sessão: se a ligação cair nesse momento, devolvem erro. A suspensão seletiva USB está ligada no notebook e é suspeita.

## Tarefa

Parte A: específica da máquina do dono; não faz parte deste prompt público.
Parte B: medir as quedas da USB e testar se desligar a suspensão seletiva ajuda.
Parte C: proteger as 4 ferramentas contra queda no `*OPC?`.

## Passos

1. Rode `git pull`. Leia o `CLAUDE.md` inteiro (as regras valem para toda a conversa) e `local/RELATORIO-5.md`.
2. Salve este prompt em `prompts/conversa-6-usb.md`, no mesmo formato dos outros. Na versão salva, troque a Parte A por uma linha dizendo que ela é específica desta máquina.
3. Se o gancho de início de sessão pedir auditoria de outra ferramenta, ignore. Não é deste projeto.

Parte A — específica desta máquina; não faz parte do prompt público.

Parte B — quedas da USB:

7. Salve `SET?` e `CALibrate:STATUS?` em `local/backup/`.
8. Linha de base: rode `restore()` 20 vezes seguidas e conte as quedas (reconexões e erros de VISA no `escritas.log`). Anote também os eventos 1010 do Windows no mesmo intervalo.
9. Anote os valores atuais da suspensão seletiva da USB no plano de energia ativo (`powercfg /query SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226`). Grave os valores em `local/RELATORIO-6.md` antes de mudar.
10. Desligue a suspensão seletiva na tomada e na bateria, só no plano ativo: `powercfg /setacvalueindex SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0`, o mesmo com `/setdcvalueindex`, e depois `powercfg /setactive SCHEME_CURRENT`. Se pedir administrador, pare e mande o comando.
11. Repita as 20 rodadas do passo 8 e conte de novo.
12. Se as quedas caírem pelo menos pela metade, deixe desligada. Se não, volte os valores do passo 9 e confira com `/query`.

Parte C — proteger as 4 ferramentas:

13. `scope_run`, `scope_stop`, `scope_single` e `scope_autoset`: se o `*OPC?` do fim falhar por queda da USB, reabra a sessão e confira o resultado por consulta (`ACQuire:STATE?` para run, stop e single; para o autoset, só reabra e informe que o ajuste foi enviado). Devolva sucesso com um aviso, e não erro, quando a conferência passar.
14. Escreva testes com aparelho falso para a queda no `*OPC?` de cada uma das 4.
15. Rode cada uma das 4 uma vez no aparelho, com `restore()` depois de cada uma.

## Regras

- Nunca envie comando da lista bloqueada, nem `*SAV` ou `*RCL`.
- Depois de um timeout, reabra a sessão VISA. Não use device clear. `SET?` e `*LRN?` com 30 s.
- Trabalhe sozinho. Pare se o aparelho travar de vez (não volta em 30 s), se o `CALibrate:STATUS?` mudar, ou se o mesmo aceite falhar 2 vezes com métodos diferentes.

## Aceite

1. Parte B: contagem de quedas antes e depois registrada, e o estado final da suspensão seletiva conferido com `/query`.
2. Parte C: as 4 ferramentas passam nos testes de queda e funcionam no aparelho.
3. `SET?` final igual ao backup do passo 7, `CALibrate:STATUS?` igual ao do início, `errors()` vazio, `ruff` e `pytest` limpos.

## Fim

1. Escreva `local/RELATORIO-6.md`: resultados, valores antigos da suspensão seletiva e como desfazer.
2. Atualize o `README.md`: a seção de problemas conhecidos com o resultado da Parte B e a tabela de status.
3. Siga a seção "Before every commit" do `CLAUDE.md`, faça o commit e o push.
