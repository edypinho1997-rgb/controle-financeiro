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
gunicorn wsgi:app
```

### Observação importante

O banco atual é SQLite. Para poucas pessoas pode servir em algumas hospedagens, mas se depois você quiser algo mais forte e compartilhado com mais segurança, o próximo passo ideal é migrar para PostgreSQL.
