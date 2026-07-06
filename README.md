# Radar Full Gutos Car — v11 custos e configuração por planilha

Versão baseada na v10 estável, com novos campos editáveis:

- estoque_minimo
- estoque_recomendado
- observacao
- custo_produto
- custo_mercado_livre
- custo_impostos

Novas funções:

- Baixar planilha de configuração com todos os anúncios.
- Importar planilha preenchida para atualizar os campos editáveis em lote.
- A importação do relatório de anúncios também aceita essas colunas opcionais. Células em branco preservam o valor já salvo no banco.

Rotas novas:

- `/exportar-configuracao`
- `/importar-configuracao`

Para atualizar a versão atual no GitHub, substitua principalmente:

- `app.py`
- `templates/base.html`
- `templates/produto.html`
- `templates/importar.html`
- adicione `templates/importar_configuracao.html`

Os dados continuam salvos no PostgreSQL via `DATABASE_URL`.
