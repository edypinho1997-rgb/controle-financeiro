# Controle Financeiro Web

## Rodar localmente

```bash
python -m pip install -r requirements.txt
python app_web.py
```

Abra:

```text
http://127.0.0.1:5000
```

## Arquivos principais

- `app_web.py`: app Flask
- `wsgi.py`: entrada para deploy
- `Procfile`: start command para plataformas compatíveis
- `render.yaml`: exemplo de deploy no Render
- `financeiro_web.db`: banco SQLite criado automaticamente

## Deploy

### Render

1. Suba o projeto para o GitHub
2. Crie um novo Web Service no Render
3. Conecte o repositório
4. O Render pode usar o `render.yaml` automaticamente

Start command:

```text
gunicorn --bind 0.0.0.0:$PORT wsgi:app
```

### Observação importante

O banco atual é SQLite. Em plano grátis do Render, o sistema sobe, mas os dados locais podem ser perdidos em restart ou redeploy porque o filesystem é efêmero. Para uso estável, o próximo passo ideal é migrar para PostgreSQL.
