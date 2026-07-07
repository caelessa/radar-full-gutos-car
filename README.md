# Radar Full Gutos Car - v14 Reposição ZERADO?

Baseada na versão robusta com PostgreSQL, custos e planilha de configuração.

## Alteração principal

A coluna **Reposição** agora pode mostrar:

- `SIM`: produto presente no relatório e abaixo/igual ao estoque mínimo.
- `NÃO`: produto sem necessidade crítica de reposição.
- `ZERADO?`: produto não apareceu no último relatório, mas tinha estoque Full registrado anteriormente. O sistema considera como possível estoque zerado e destaca em amarelo para conferência do usuário.

## Cálculo para ZERADO?

Quando o anúncio fica como `ZERADO?`, a quantidade a enviar considera o estoque atual como 0:

- Se houver `estoque_recomendado`, enviar = estoque_recomendado.
- Se não houver recomendado, enviar = estoque_minimo.

## Arquivos principais alterados

- `app.py`
- `templates/index.html`

## Observação

A exportação CSV de reposição também passa a incluir os itens marcados como `ZERADO?`.


## v15 - Confirmar zerado

Adicionado botão **Confirmar zerado** para anúncios marcados como `ZERADO?`.

Ao confirmar, o sistema:

- grava `quantidade_full = 0`;
- marca `zerado_confirmado = TRUE`;
- adiciona uma observação automática com data e hora;
- mantém `No relatório = NÃO`;
- passa a tratar o item como reposição `SIM`, usando estoque recomendado ou mínimo para calcular a quantidade a enviar.


## Versão 16 - Excluir da base

Para itens marcados como `ZERADO?`, agora existem duas ações:

- **Confirmar zerado**: usado quando o estoque realmente acabou no Full. Atualiza `quantidade_full = 0` e mantém o item na reposição.
- **Excluir da base**: usado quando o anúncio foi retirado do Full ou não deve mais ser controlado. Remove o registro de `anuncios_full`. Se o anúncio voltar em um relatório futuro, a importação irá cadastrá-lo novamente automaticamente.
