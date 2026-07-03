# Radar Full Gutos Car - PostgreSQL

Versão web Flask usando PostgreSQL via variável `DATABASE_URL`.

## Variáveis no Render

Crie uma variável de ambiente:

```text
DATABASE_URL=<string de conexão PostgreSQL>
```

Opcional:

```text
SECRET_KEY=uma-chave-qualquer
```

## Comandos no Render

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn app:app
```

## Observação

Na primeira execução, a aplicação cria a tabela `anuncios_full` no PostgreSQL. Se a tabela estiver vazia, ela carrega automaticamente os dados iniciais do arquivo `radar_full_gutos.db` incluído no projeto.

Depois disso, alterações de estoque mínimo/recomendado e importações ficam salvas no PostgreSQL, não no disco temporário do Render.
