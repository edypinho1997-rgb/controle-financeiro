import os

from flask import Flask, flash, redirect, render_template, request, session, url_for
from supabase import create_client


TIPOS = {
    "entrada": "Entrada",
    "saida": "Saida",
    "investimento": "Investimento",
}

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ihabovtuabftonodxoqv.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_Wg-oqkTtUNv814BF2lAu_g_8MHA1sId")
LOGIN_USER = os.environ.get("LOGIN_USER", "edypinheiro")
LOGIN_PASSWORD = os.environ.get("LOGIN_PASSWORD", "controle123")
LANCAMENTOS_TABLE = "lancamentos"
MARIA_TABLE = "maria_cecilia"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "controle-financeiro-secret")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


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


def normalizar_data(texto):
    texto = (texto or "").strip()
    if len(texto) == 10 and texto[4] == "-" and texto[7] == "-":
        ano, mes, dia = texto.split("-")
        return f"{dia}/{mes}/{ano}"
    return texto


def redirecionar_para(secao=None):
    destino = url_for("index")
    if secao:
        destino = f"{destino}#{secao}"
    return redirect(destino)


def buscar_lancamentos():
    try:
        resposta = (
            supabase.table(LANCAMENTOS_TABLE)
            .select("id,tipo,nome,data,valor")
            .order("id", desc=True)
            .execute()
        )
        return resposta.data or []
    except Exception as e:
        print("Erro ao buscar lancamentos:", e)
        return []


def buscar_itens_maria():
    try:
        resposta = (
            supabase.table(MARIA_TABLE)
            .select("id,nome,valor,comprado")
            .order("id", desc=True)
            .execute()
        )
        return resposta.data or []
    except Exception as e:
        print("Erro ao buscar Maria Cecilia:", e)
        return []


def calcular_resumo(historico):
    totais = {tipo: 0.0 for tipo in TIPOS}

    for item in historico:
        tipo = item.get("tipo", "")
        if tipo in totais:
            totais[tipo] += float(item.get("valor", 0) or 0)

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


def calcular_total_maria(itens_maria):
    return sum(float(item.get("valor", 0) or 0) for item in itens_maria)


def montar_resumo_texto(resumo, historico):
    return (
        f"Entrada total de {formatar_real(resumo['entrada'])}, "
        f"saidas em {formatar_real(resumo['saida'])}, "
        f"investimentos em {formatar_real(resumo['investimento'])} "
        f"e saldo atual de {formatar_real(resumo['saldo'])}. "
        f"Voce tem {len(historico)} lancamentos no historico."
    )


@app.before_request
def exigir_login():
    rotas_livres = {"login", "static"}
    if request.endpoint in rotas_livres:
        return

    if not session.get("autenticado"):
        return redirect(url_for("login"))


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
    historico = buscar_lancamentos()
    resumo = calcular_resumo(historico)
    resumo_texto = montar_resumo_texto(resumo, historico)

    return render_template(
        "index.html",
        resumo=resumo,
        historico=historico,
        resumo_texto=resumo_texto,
    )


@app.get("/maria/fragment")
def maria_fragment():
    itens_maria = buscar_itens_maria()
    return render_template(
        "partials/maria_section.html",
        itens_maria=itens_maria,
        maria_total=calcular_total_maria(itens_maria),
    )


@app.post("/lancamentos")
def adicionar_lancamento():
    tipo = request.form.get("tipo", "").strip()
    if tipo not in TIPOS:
        return redirecionar_para("topo")

    nome = request.form.get("nome", "").strip()
    data_texto = normalizar_data(request.form.get("data", ""))
    valor = ler_valor(request.form.get("valor", "0"))

    if not nome or valor <= 0:
        return redirecionar_para(tipo)

    try:
        supabase.table(LANCAMENTOS_TABLE).insert({
            "tipo": tipo,
            "nome": nome,
            "data": data_texto,
            "valor": valor,
        }).execute()
    except Exception as e:
        print("Erro ao salvar lancamento:", e)
        flash("Nao foi possivel salvar no Supabase.")

    return redirecionar_para(tipo)


@app.post("/lancamentos/<int:item_id>/apagar")
def apagar_lancamento(item_id):
    try:
        supabase.table(LANCAMENTOS_TABLE).delete().eq("id", item_id).execute()
    except Exception as e:
        print("Erro ao apagar lancamento:", e)
        flash("Nao foi possivel apagar no Supabase.")
    return redirecionar_para("historico")


@app.post("/maria")
def adicionar_item_maria():
    nome = request.form.get("nome", "").strip()
    if not nome:
        return redirecionar_para("maria")

    try:
        supabase.table(MARIA_TABLE).insert({
            "nome": nome,
            "valor": 0,
            "comprado": False,
        }).execute()
    except Exception as e:
        print("Erro ao adicionar item Maria Cecilia:", e)
        flash("Crie a tabela maria_cecilia no Supabase para usar essa aba.")

    return redirecionar_para("maria")


@app.post("/maria/<int:item_id>/apagar")
def apagar_item_maria(item_id):
    try:
        supabase.table(MARIA_TABLE).delete().eq("id", item_id).execute()
    except Exception as e:
        print("Erro ao apagar item Maria Cecilia:", e)
        flash("Nao foi possivel apagar na Maria Cecilia.")
    return redirecionar_para("maria")


@app.post("/maria/<int:item_id>/atualizar")
def atualizar_item_maria(item_id):
    try:
        supabase.table(MARIA_TABLE).update({
            "valor": ler_valor(request.form.get("valor", "0")),
            "comprado": request.form.get("comprado") == "on",
        }).eq("id", item_id).execute()
    except Exception as e:
        print("Erro ao atualizar item Maria Cecilia:", e)
        flash("Nao foi possivel atualizar a Maria Cecilia.")
    return redirecionar_para("maria")


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=False)
