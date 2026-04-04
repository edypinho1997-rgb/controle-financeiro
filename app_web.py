import json
import os
import sqlite3
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
JSON_PATH = BASE_DIR / "dados.json"
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "financeiro_web.db"))

TIPOS = {
    "entrada": "Entrada",
    "saida": "Saida",
    "investimento": "Investimento",
}


app = Flask(__name__)


def formatar_real(valor):
    inteiro, decimal = f"{float(valor):,.2f}".split(".")
    inteiro = inteiro.replace(",", ".")
    return f"R$ {inteiro},{decimal}"


def ler_valor(texto):
    texto = (texto or "").strip().replace("R$", "").replace(" ", "")
    if not texto:
        return 0.0
    texto = texto.replace(".", "").replace(",", ".")
    return float(texto)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            nome TEXT NOT NULL,
            data TEXT DEFAULT '',
            valor REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS maria_cecilia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            valor REAL NOT NULL DEFAULT 0,
            comprado INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    db.commit()


with app.app_context():
    init_db()


def importar_json_se_necessario():
    db = get_db()
    total_lancamentos = db.execute("SELECT COUNT(*) FROM lancamentos").fetchone()[0]
    total_maria = db.execute("SELECT COUNT(*) FROM maria_cecilia").fetchone()[0]
    if total_lancamentos or total_maria or not JSON_PATH.exists():
        return

    try:
        with JSON_PATH.open("r", encoding="utf-8") as arquivo:
            data = json.load(arquivo)
    except (json.JSONDecodeError, OSError):
        return

    for item in data.get("dados", []):
        db.execute(
            "INSERT INTO lancamentos (tipo, nome, data, valor) VALUES (?, ?, ?, ?)",
            (
                item.get("tipo", ""),
                item.get("nome", ""),
                item.get("data", ""),
                float(item.get("valor", 0)),
            ),
        )

    for item in data.get("maria_cecilia", []):
        db.execute(
            "INSERT INTO maria_cecilia (nome, valor, comprado) VALUES (?, ?, ?)",
            (
                item.get("nome", ""),
                float(item.get("valor", 0)),
                1 if item.get("comprado") else 0,
            ),
        )

    db.commit()


@app.before_request
def preparar_banco():
    init_db()
    importar_json_se_necessario()


def buscar_lancamentos():
    db = get_db()
    return db.execute(
        "SELECT id, tipo, nome, data, valor FROM lancamentos ORDER BY id DESC"
    ).fetchall()


def buscar_itens_maria():
    db = get_db()
    return db.execute(
        "SELECT id, nome, valor, comprado FROM maria_cecilia ORDER BY id DESC"
    ).fetchall()


def calcular_resumo():
    db = get_db()
    totais = {tipo: 0.0 for tipo in TIPOS}

    for linha in db.execute(
        "SELECT tipo, COALESCE(SUM(valor), 0) AS total FROM lancamentos GROUP BY tipo"
    ).fetchall():
        totais[linha["tipo"]] = float(linha["total"] or 0)

    entrada = totais["entrada"]
    saida = totais["saida"]
    investimento = totais["investimento"]
    saldo = entrada - saida - investimento
    base = entrada if entrada > 0 else 1

    return {
        "entrada": entrada,
        "saida": saida,
        "investimento": investimento,
        "saldo": saldo,
        "percentual_saida": max(0, (saida / base) * 100),
        "percentual_investimento": max(0, (investimento / base) * 100),
        "percentual_livre": max(0, 100 - ((saida / base) * 100) - ((investimento / base) * 100)),
    }


def redirecionar_para(secao=None):
    destino = url_for("index")
    if secao:
        destino = f"{destino}#{secao}"
    return redirect(destino)


@app.context_processor
def inject_helpers():
    return {"formatar_real": formatar_real, "TIPOS": TIPOS}


@app.get("/")
def index():
    resumo = calcular_resumo()
    historico = buscar_lancamentos()
    itens_maria = buscar_itens_maria()
    maria_total = sum(float(item["valor"] or 0) for item in itens_maria)

    return render_template(
        "index.html",
        resumo=resumo,
        historico=historico,
        itens_maria=itens_maria,
        maria_total=maria_total,
    )


@app.post("/lancamentos")
def adicionar_lancamento():
    tipo = request.form.get("tipo", "").strip()
    if tipo not in TIPOS:
        return redirecionar_para("topo")

    nome = request.form.get("nome", "").strip()
    data_texto = request.form.get("data", "").strip()
    valor = ler_valor(request.form.get("valor", "0"))

    if not nome or valor <= 0:
        return redirecionar_para(tipo)

    db = get_db()
    db.execute(
        "INSERT INTO lancamentos (tipo, nome, data, valor) VALUES (?, ?, ?, ?)",
        (tipo, nome, data_texto, valor),
    )
    db.commit()
    return redirecionar_para(tipo)


@app.post("/lancamentos/<int:item_id>/apagar")
def apagar_lancamento(item_id):
    db = get_db()
    db.execute("DELETE FROM lancamentos WHERE id = ?", (item_id,))
    db.commit()
    return redirecionar_para("historico")


@app.post("/maria")
def adicionar_item_maria():
    nome = request.form.get("nome", "").strip()
    if not nome:
        return redirecionar_para("maria")

    db = get_db()
    db.execute(
        "INSERT INTO maria_cecilia (nome, valor, comprado) VALUES (?, 0, 0)",
        (nome,),
    )
    db.commit()
    return redirecionar_para("maria")


@app.post("/maria/<int:item_id>/apagar")
def apagar_item_maria(item_id):
    db = get_db()
    db.execute("DELETE FROM maria_cecilia WHERE id = ?", (item_id,))
    db.commit()
    return redirecionar_para("maria")


@app.post("/maria/<int:item_id>/atualizar")
def atualizar_item_maria(item_id):
    valor = ler_valor(request.form.get("valor", "0"))
    comprado = 1 if request.form.get("comprado") == "on" else 0

    db = get_db()
    db.execute(
        "UPDATE maria_cecilia SET valor = ?, comprado = ? WHERE id = ?",
        (valor, comprado, item_id),
    )
    db.commit()
    return redirecionar_para("maria")


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=False)
