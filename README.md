# Radar Full Gutos Car - versão web online

Aplicação Flask para controle de reposição do estoque Mercado Livre Full.

## Rodar localmente

```bash
pip install -r requirements.txt
python app.py
```

Acesse:

```text
http://127.0.0.1:5000
```

## Publicar no Render

1. Crie um repositório no GitHub e envie todos os arquivos desta pasta.
2. No Render, clique em **New > Web Service**.
3. Conecte o repositório.
4. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Crie o serviço.

## Observação importante sobre banco SQLite

O banco `radar_full_gutos.db` está dentro do projeto e funciona localmente.

Em hospedagens gratuitas como Render, alterações no SQLite podem ser perdidas em redeploy/reinício se não houver disco persistente. Para uso real contínuo, use uma destas opções:

- Render com Persistent Disk;
- servidor/VPS;
- migrar depois para PostgreSQL.

## Fluxo de uso

1. Abrir o dashboard.
2. Importar relatório atualizado do Mercado Livre.
3. Conferir anúncios novos, ausentes e alterados.
4. Cadastrar estoque mínimo e recomendado.
5. Exportar lista de reposição.
