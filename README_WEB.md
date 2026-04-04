# Controle Financeiro Web

## Rodar localmente

```bash
python -m pip install -r requirements-web.txt
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

O app aceita `DATABASE_URL`. Sem essa variável, ele usa SQLite local. Para salvar de forma persistente online, configure um Postgres no Supabase e cole a connection string no Render como `DATABASE_URL`.
