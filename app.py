import locale
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')  # Para sistemas Linux
except locale.Error:
    locale.setlocale(locale.LC_TIME, '')  # Fallback para o padrão do sistema
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time, timedelta
from extensoes import db
from models import Funcionario, Empresa, Ponto

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///controle_ponto.db'
db.init_app(app)

# Função auxiliar para lidar com campos de horário vazios
def limpar_horario(valor):
    return valor if valor else None

@app.template_filter('horario_formatado')
def horario_formatado(value):
    if not value:
        return "00:00"
    total_minutes = int(value.total_seconds() // 60)
    horas = total_minutes // 60
    minutos = total_minutes % 60
    return f"{horas:02d}:{minutos:02d}"

@app.route("/")
def index():
    return redirect(url_for("registro"))

@app.route("/funcionarios", methods=["GET", "POST"])
def cadastro_funcionario():
    if request.method == "POST":
        nome = request.form["nome"]
        novo_funcionario = Funcionario(nome=nome)
        db.session.add(novo_funcionario)
        db.session.commit()
        return redirect(url_for("cadastro_funcionario"))

    funcionarios = Funcionario.query.order_by(Funcionario.nome.asc()).all()
    return render_template("cadastro_funcionario.html", funcionarios=funcionarios)

@app.route("/cadastro_empresa", methods=["GET", "POST"])
def cadastro_empresa():
    if request.method == "POST":
        nome = request.form["nome"]
        vale = request.form["vale_alimentacao"]
        nova_empresa = Empresa(nome=nome, vale_alimentacao=vale)
        db.session.add(nova_empresa)
        db.session.commit()
        return redirect(url_for("cadastro_empresa"))

    empresas = Empresa.query.order_by(Empresa.nome.asc()).all()
    return render_template("cadastro_empresa.html", empresas=empresas)

@app.route("/lista-registros", methods=["GET"])
def lista_registros():
    funcionarios = Funcionario.query.order_by(Funcionario.nome.asc()).all()
    empresas = Empresa.query.order_by(Empresa.nome.asc()).all()

    query = Ponto.query
    funcionario_id = request.args.get("funcionario_id")
    empresa_id = request.args.get("empresa_id")
    data_ini = request.args.get("data_ini")
    data_fim = request.args.get("data_fim")

    if funcionario_id:
        query = query.filter_by(funcionario_id=funcionario_id)
    if empresa_id:
        query = query.filter_by(empresa_id=empresa_id)
    if data_ini:
        query = query.filter(Ponto.data >= data_ini)
    if data_fim:
        query = query.filter(Ponto.data <= data_fim)

    pontos = query.order_by(Ponto.data.asc()).all()

    INIDIA = time(5, 0)
    FIMDIA = time(22, 0)
    ININOT = time(22, 0)
    FIMNOT = time(5, 0)

    def to_time(valor):
        if isinstance(valor, str):
            return datetime.strptime(valor, "%H:%M").time()
        return valor

    for ponto in pontos:
        if isinstance(ponto.data, str):
            ponto.data_obj = datetime.strptime(ponto.data, "%Y-%m-%d")
        else:
            ponto.data_obj = ponto.data

        ponto.horas_diurnas = timedelta()
        ponto.horas_diurnas_reais = timedelta()
        ponto.horas_noturnas_reais = timedelta()
        ponto.horas_noturnas = timedelta()
        ponto.horas_adicional = timedelta()
        ponto.horas_adicional_ficta = timedelta()
        ponto.horas_fictas = timedelta()
        ponto.horas_total = timedelta()
        ponto.extra_50_diurno = timedelta()
        ponto.extra_50_noturno_reais = timedelta()
        ponto.extra_100_diurno = timedelta()
        ponto.extra_100_noturno = timedelta()
        ponto.horas_normais = timedelta(hours=8) if ponto.data_obj.weekday() < 5 else timedelta(hours=4)

        turnos = [(ponto.entrada1, ponto.saida1), (ponto.entrada2, ponto.saida2), (ponto.entrada3, ponto.saida3)]
        minutos_marcados = []

        for entrada, saida in turnos:
            if entrada and saida:
                entrada = to_time(entrada)
                saida = to_time(saida)

                entrada_dt = datetime.combine(ponto.data_obj, entrada)
                saida_dt = datetime.combine(ponto.data_obj, saida)
                if saida < entrada:
                    saida_dt += timedelta(days=1)

                atual = entrada_dt
                while atual < saida_dt:
                    minutos_marcados.append(atual)
                    atual += timedelta(minutes=1)

        for minuto in minutos_marcados:
            hora = minuto.time()
            tipo = "diurna"
            if hora >= ININOT or hora < FIMNOT:
                tipo = "noturna"

            if minuto.weekday() == 6:
                if tipo == "diurna":
                    ponto.extra_100_diurno += timedelta(minutes=1)
                    ponto.horas_diurnas_reais += timedelta(minutes=1)
                else:
                    ponto.extra_100_noturno += timedelta(minutes=1)
                    ponto.horas_noturnas_reais += timedelta(minutes=1)
                continue
            elif ponto.data_obj.weekday() == 5 and minuto.date() > ponto.data_obj.date():
                if tipo == "diurna":
                    ponto.extra_100_diurno += timedelta(minutes=1)
                    ponto.horas_diurnas_reais += timedelta(minutes=1)
                else:
                    ponto.extra_100_noturno += timedelta(minutes=1)
                    ponto.horas_noturnas_reais += timedelta(minutes=1)
                continue

            if ponto.horas_normais > timedelta():
                ponto.horas_normais -= timedelta(minutes=1)
                if tipo == "diurna":
                    ponto.horas_diurnas += timedelta(minutes=1)
                    ponto.horas_diurnas_reais += timedelta(minutes=1)
                else:
                    ponto.horas_noturnas_reais += timedelta(minutes=1)
                    ponto.horas_adicional += timedelta(minutes=1)
            else:
                if tipo == "diurna":
                    ponto.extra_50_diurno += timedelta(minutes=1)
                    ponto.horas_diurnas_reais += timedelta(minutes=1)
                else:
                    ponto.extra_50_noturno_reais += timedelta(minutes=1)
                    ponto.horas_noturnas_reais += timedelta(minutes=1)


        ponto.horas_fictas = ponto.horas_noturnas_reais * 0.142857 # 03:40 * 0.14 = 00:31

        ponto.horas_adicional_ficta = ponto.horas_adicional * 0.142857 # 02:00 * 0.14 = 00:17

        ponto.horas_noturnas = ponto.horas_noturnas_reais + ponto.horas_fictas 
        
        ponto.horas_normais = timedelta(hours=8) if ponto.data_obj.weekday() < 5 else timedelta(hours=4)
        
        ponto.extra_100_noturno = ponto.extra_100_noturno * 1.142857

        ponto.horas_total = ponto.horas_diurnas_reais + ponto.horas_noturnas

        carga_horaria_diaria = timedelta(hours=8) if ponto.data_obj.weekday() < 5 else timedelta(hours=4)

        jornada_total = ponto.horas_diurnas_reais + ponto.horas_noturnas_reais + ponto.horas_fictas

        extra_total = max(timedelta(), jornada_total - carga_horaria_diaria)

        horas_normais_noturnas_total = max(timedelta(), ponto.horas_noturnas - extra_total)

        ponto.adicional_noturno = horas_normais_noturnas_total

        ponto.extra_50_noturno = ponto.horas_noturnas - ponto.adicional_noturno

        if jornada_total < carga_horaria_diaria:
            ponto.horas_normais = jornada_total
        else:
            ponto.horas_normais = carga_horaria_diaria

        


    return render_template("lista_registros.html", pontos=pontos, funcionarios=funcionarios, empresas=empresas, teste=ponto.extra_50_noturno_reais)

@app.route("/registro", methods=["GET", "POST"])
def registro():
    funcionarios = Funcionario.query.order_by(Funcionario.nome.asc()).all()
    empresas = Empresa.query.order_by(Empresa.nome.asc()).all()

    if request.method == "POST":
        funcionario_id = request.form["funcionario_id"]
        empresa_id = request.form["empresa_id"]
        data = request.form["data"]

        novo_ponto = Ponto(
            funcionario_id=funcionario_id,
            empresa_id=empresa_id,
            data=data,
            entrada1=limpar_horario(request.form["entrada1"]),
            saida1=limpar_horario(request.form["saida1"]),
            entrada2=limpar_horario(request.form["entrada2"]),
            saida2=limpar_horario(request.form["saida2"]),
            entrada3=limpar_horario(request.form["entrada3"]),
            saida3=limpar_horario(request.form["saida3"])
        )

        db.session.add(novo_ponto)
        db.session.commit()
        return redirect(url_for("registro"))
 
    pontos = Ponto.query.order_by(Ponto.data.asc()).all()
    for ponto in pontos:
        if isinstance(ponto.data, str):
            ponto.data = datetime.strptime(ponto.data, "%Y-%m-%d")

    return render_template("registro.html", funcionarios=funcionarios, empresas=empresas, pontos=pontos)

@app.route("/excluir_ponto/<int:id>")
def excluir_ponto(id):
    ponto = Ponto.query.get_or_404(id)
    db.session.delete(ponto)
    db.session.commit()
    return redirect(url_for("registro"))

@app.route("/excluir_funcionario/<int:id>")
def excluir_funcionario(id):
    funcionario = Funcionario.query.get_or_404(id)
    db.session.delete(funcionario)
    db.session.commit()
    return redirect(url_for("cadastro_funcionario"))

@app.route("/excluir_empresa/<int:id>")
def excluir_empresa(id):
    empresa = Empresa.query.get_or_404(id)
    db.session.delete(empresa)
    db.session.commit()
    return redirect(url_for("cadastro_empresa"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
