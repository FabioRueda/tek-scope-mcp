# Conversa 4 de 4 — Servidor MCP (`server.py`)

- **Modelo:** Sonnet 5.5 (`sonnet`)
- **Esforço:** `medium`
- **Abrir com:** `claude --model sonnet --effort medium`
- **Motivo:** é embrulhar a biblioteca pronta; trabalho mecânico.
- **Se falhar duas vezes no mesmo aceite:** `/model opus`.

## Antes de começar (pessoa)

1. Osciloscópio ligado e conectado por USB.

## Contexto

Osciloscópio Tektronix TDS 1012C-EDU, firmware v25.11, ligado por USB a um notebook Windows. Leia `CLAUDE.md`, `local/ESTADO.md`, `local/RELATORIO-2.md`, `local/RELATORIO-3.md` e `tek_scope.py`.

## Tarefa

Expor o `tek_scope.py` como servidor MCP local (stdio), para o Claude Code e para o app Claude desktop.

## Ferramentas

- Leitura, sem confirmação: `scope_idn`, `scope_state`, `scope_errors`, `scope_query(cmd)` (uma consulta por chamada; recusa a lista bloqueada), `scope_measure(tipo, canal)`, `scope_waveform(canal)` (devolve estatísticas, caminho do CSV e no máximo 500 pontos), `scope_screenshot()` (devolve a imagem).
- Ajuste, exigem `confirm=true`: `scope_set_channel`, `scope_set_timebase`, `scope_set_trigger`, `scope_set_acquisition`, `scope_run`, `scope_stop`, `scope_single`, `scope_autoset`, `scope_write(cmd)`.
- Nenhuma ferramenta libera a lista bloqueada. `allow_dangerous` não existe no servidor.
- `TEK_SCOPE_READONLY=1` remove todas as ferramentas de ajuste.

## Passos

1. Use o SDK MCP oficial para Python, versão atual.
2. Abra a conexão VISA sob demanda e feche depois de cada chamada.
3. Teste cada ferramenta de leitura uma vez contra o aparelho real.
4. Registre no Claude Code em escopo de usuário: `claude mcp add --scope user tek-scope -- <python do venv> <caminho absoluto do server.py>`.
5. App Claude desktop: descubra como os servidores MCP locais já existentes estão registrados e registre o `tek-scope` do mesmo jeito. Mostre o diff do arquivo de configuração antes de salvar e guarde uma cópia `.bak`.
6. Atualize o `README.md`, em inglês: instalação, ferramentas, lista bloqueada, como desligar.

## Regras

- Trabalhe sozinho. Pare só em falha depois de 2 tentativas diferentes.
- O caminho absoluto do registro fica só na máquina. Não vai para o repositório.

## Aceite

1. `claude mcp list` mostra `tek-scope` conectado.
2. `scope_idn` e `scope_screenshot` funcionam pelo Claude Code.
3. `ruff` e `pytest` limpos.

## Fim

1. Escreva `local/RELATORIO-4.md`.
2. Siga a seção "Before every commit" do `CLAUDE.md`, faça o commit e o push.
3. Mostre o resumo e avise a pessoa para fechar e reabrir o app Claude desktop.
