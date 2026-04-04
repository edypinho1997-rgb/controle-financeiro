import os
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy


TIPOS = {
    "entrada": "Entrada",
    "saida": "Saida",
    "investimento": "Investimento",
}

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'financeiro_web.db')}"

LOGIN_USER = os.environ.get("LOGIN_USER", "edypinheiro")
LOGIN_PASSWORD = os.environ.get("LOGIN_PASSWORD", "controle123")


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.environ.get("SECRET_KEY", "controle-financeiro-secret")

if DATABASE_URL.startswith("postgresql://"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"sslmode": "require"}
    }

db = SQLAlchemy(app)


class Lancamento(db.Model):
    __tablename__ = "lancamentos"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(30), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    data = db.Column(db.String(20), default="")
    valor = db.Column(db.Float, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ItemMariaCecilia(db.Model):
    __tablename__ = "maria_cecilia"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, default=0, nullable=False)
    comprado = db.Column(db.Boolean, default=False, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


with app.app_context():
    db.create_all()

    inspector = db.inspect(db.engine)

    colunas_lancamentos = {coluna["name"] for coluna in inspector.get_columns("lancamentos")} if inspector.has_table("lancamentos") else set()
    if "criado_em" not in colunas_lancamentos:
        db.session.execute(db.text("ALTER TABLE lancamentos ADD COLUMN criado_em DATETIME"))
        db.session.commit()

    colunas_maria = {coluna["name"] for coluna in inspector.get_columns("maria_cecilia")} if inspector.has_table("maria_cecilia") else set()
    if "criado_em" not in colunas_maria:
        db.session.execute(db.text("ALTER TABLE maria_cecilia ADD COLUMN criado_em DATETIME"))
        db.session.commit()


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


@app.before_request
def exigir_login():
    rotas_livres = {"login", "static"}
    if request.endpoint in rotas_livres:
        return

    if not session.get("autenticado"):
        return redirect(url_for("login"))


def calcular_resumo():
    totais = {tipo: 0.0 for tipo in TIPOS}
    resultados = (
        db.session.query(Lancamento.tipo, db.func.coalesce(db.func.sum(Lancamento.valor), 0))
        .group_by(Lancamento.tipo)
        .all()
    )

    for tipo, total in resultados:
        totais[tipo] = float(total or 0)

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


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("autenticado"):
        return redirect(url_for("index"))

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")

        if usuario == LOGIN_USER and senha == LOGIN_PASSWORD:
            session["autenticado"] = True
            return redirect(url_for("index"))

        flash("Usuario ou senha invalidos.")

    return render_template("login.html")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
def index():
    resumo = calcular_resumo()
    historico = Lancamento.query.order_by(Lancamento.id.desc()).all()
    itens_maria = ItemMariaCecilia.query.order_by(ItemMariaCecilia.id.desc()).all()
    maria_total = sum(float(item.valor or 0) for item in itens_maria)

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

    db.session.add(Lancamento(tipo=tipo, nome=nome, data=data_texto, valor=valor))
    db.session.commit()
    return redirecionar_para(tipo)


@app.post("/lancamentos/<int:item_id>/apagar")
def apagar_lancamento(item_id):
    item = Lancamento.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirecionar_para("historico")


@app.post("/maria")
def adicionar_item_maria():
    nome = request.form.get("nome", "").strip()
    if not nome:
        return redirecionar_para("maria")

    db.session.add(ItemMariaCecilia(nome=nome, valor=0, comprado=False))
    db.session.commit()
    return redirecionar_para("maria")


@app.post("/maria/<int:item_id>/apagar")
def apagar_item_maria(item_id):
    item = ItemMariaCecilia.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return redirecionar_para("maria")


@app.post("/maria/<int:item_id>/atualizar")
def atualizar_item_maria(item_id):
    item = ItemMariaCecilia.query.get_or_404(item_id)
    item.valor = ler_valor(request.form.get("valor", "0"))
    item.comprado = request.form.get("comprado") == "on"
    db.session.commit()
    return redirecionar_para("maria")


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=False)
