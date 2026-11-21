# Conversa 1 de 4 — Conexão com o osciloscópio

- **Modelo:** Opus 5.5 (`opus`)
- **Esforço:** `high`
- **Abrir com:** `claude --model opus --effort high`
- **Motivo:** driver USB no Windows é a etapa que mais falha.

## Antes de começar (pessoa)

1. Ligue o osciloscópio e conecte o cabo na porta USB traseira (USB Device).
2. No painel: Utility ► Options ► Rear USB Port ► Computer. Se o menu tiver outro nome, confira no manual do usuário.
3. Fique por perto: o instalador do driver pede o UAC e o aceite da licença.

## Contexto

Osciloscópio Tektronix TDS 1012C-EDU, firmware v25.11, do dono deste repositório, ligado pela porta USB Device traseira a um notebook Windows. Leia `CLAUDE.md` antes de tudo: as regras de lá valem aqui.

## Tarefa

Fazer o Python enxergar o aparelho e responder `*IDN?`. Nenhuma biblioteca ainda.

## Passos

1. Crie o venv `.venv` (Python 3.11 ou mais novo). Instale, sem fixar versão: `pyvisa pyvisa-py pyusb numpy pillow matplotlib ruff pytest`. Grave `requirements.txt` só com os nomes.
2. Diagnóstico antes de instalar driver: liste como o Windows enumerou o aparelho (`Get-PnpDevice`, procure `VID_0699`) e rode `pyvisa-info` para ver se já existe biblioteca VISA.
3. Backend, nesta ordem:
   1. VISA já instalada: use.
   2. Sem VISA: instale o NI-VISA pelo instalador oficial da NI, só o runtime. A pessoa aprova o UAC e a licença na tela.
   3. Só se o passo anterior falhar: PARE e explique o plano Zadig + pyvisa-py. Não troque driver USB sem OK.
4. Abra o recurso `USB0::0x0699::...::INSTR` com timeout de 10 s. Envie `*CLS`, leia `*IDN?`, envie `HEADer ON` e `VERBose ON`, leia `SET?`.
5. Grave em `local/`: `ESTADO.md` (string do recurso VISA, backend e versão, resposta do `*IDN?`) e `estado-inicial.txt` (`SET?` completo).
6. Escreva `docs/connection.md`, em inglês: como instalar o backend e achar o recurso. Sem número de série e sem caminhos da máquina.

## Regras

- Trabalhe sozinho. Pare só em: troca de driver USB, pedido de login ou conta, ou falha depois de 2 tentativas diferentes.
- Comandos de escrita permitidos nesta conversa: só `*CLS`, `HEADer` e `VERBose`.

## Aceite

`*IDN?` devolve `TEKTRONIX,TDS 1012C-EDU,...` três vezes seguidas, sem erro.

## Fim

1. Escreva `local/RELATORIO-1.md`: o que instalou, o que mudou no Windows, como desfazer.
2. Siga a seção "Before every commit" do `CLAUDE.md`, faça o commit e o push.
3. Mostre o resumo.
