# Prompts de construção

These prompts are in Portuguese. Each file is one Claude Code conversation.

Cada arquivo é uma conversa do Claude Code. Rode na ordem. Só comece a próxima quando a anterior passar no aceite.

| Conversa | Arquivo | Modelo | Esforço | Abrir com |
|---|---|---|---|---|
| 1 | [conversa-1-conexao.md](conversa-1-conexao.md) | Opus 5.5 | high | `claude --model opus --effort high` |
| 2 | [conversa-2-biblioteca.md](conversa-2-biblioteca.md) | Sonnet 5.5 | medium | `claude --model sonnet --effort medium` |
| 3 | [conversa-3-mapa.md](conversa-3-mapa.md) | Opus 5.5 | high | `claude --model opus --effort high` |
| 4 | [conversa-4-mcp.md](conversa-4-mcp.md) | Sonnet 5.5 | medium | `claude --model sonnet --effort medium` |
| 5 | [conversa-5-ajustes.md](conversa-5-ajustes.md) | Sonnet 5.5 | high | `claude --model sonnet --effort high` |
| 6 | [conversa-6-usb.md](conversa-6-usb.md) | Sonnet 5.5 | high | `claude --model sonnet --effort high` |

## Como rodar

Conversa 1, em qualquer pasta:

```
Clone https://github.com/FabioRueda/tek-scope-mcp em ~/mcp-servers/tek-scope, entre na pasta, leia CLAUDE.md e execute prompts/conversa-1-conexao.md.
```

Conversas 2 a 4, com o Claude Code aberto em `~/mcp-servers/tek-scope`:

```
Leia CLAUDE.md e execute prompts/conversa-N-nome.md.
```

## Por que esses modelos

- Opus nas conversas 1 e 3: driver USB no Windows é a etapa que mais falha, e o mapa de comandos exige julgamento perto de comandos de calibração.
- Sonnet nas conversas 2 e 4: a tarefa está toda especificada.
- Se uma conversa com Sonnet falhar duas vezes no mesmo aceite, troque para Opus com `/model opus`.
