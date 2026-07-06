# Radar Full Gutos Car - v9

Correção do erro no Render/PostgreSQL:

`psycopg.errors.TooManyColumns: tables can have at most 1600 columns`

Causa: a versão anterior fazia `ALTER TABLE DROP COLUMN` e `ADD COLUMN` das colunas geradas em toda abertura da aplicação. No PostgreSQL, colunas removidas continuam ocupando metadados internos até recriar a tabela. Repetir isso muitas vezes fez a tabela atingir o limite interno.

Correção: removida a migração repetitiva do `init_db()`. Agora a aplicação não fica recriando as colunas geradas a cada acesso.

Para atualizar no GitHub, substitua principalmente:

- `app.py`

Os templates podem permanecer como estão, salvo se você quiser substituir tudo pela versão deste pacote.
