import locale
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, '') 
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, time, timedelta
from extensoes import db
from models import Funcionario, Empresa, Ponto
from babel.dates import format_datetime

app = Flask(__name__)
app.secret_key = 'é_segredo'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///controle_ponto.db'
db.init_app(app)


def limpar_horario(valor):
    return valor if valor else None

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]
        if usuario == "admin" and senha == "senha123":
            session["usuario_logado"] = True
            return redirect(url_for("registro"))
        else:
            erro = "Usuário ou senha inválidos."
    return render_template("login.html", erro=erro)


@app.route("/logout")
def logout():
    session.pop("usuario_logado", None)
    return redirect(url_for("login"))

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
    return redirect(url_for("login"))

@app.route("/funcionarios", methods=["GET", "POST"])
def cadastro_funcionario():
    
    if not session.get("usuario_logado"):
        return redirect(url_for("login"))

    if request.method == "POST":
        nome = request.form["nome"]
        cpf = request.form["cpf"]
        novo_funcionario = Funcionario(nome=nome, cpf=cpf)
        db.session.add(novo_funcionario)
        db.session.commit()
        return redirect(url_for("cadastro_funcionario"))

    funcionarios = Funcionario.query.order_by(Funcionario.nome.asc()).all()
    return render_template("cadastro_funcionario.html", funcionarios=funcionarios)

@app.route("/editar_ponto/<int:id>", methods=["POST"])
def editar_ponto(id):
    ponto = Ponto.query.get_or_404(id)
    ponto.funcionario_id = request.form["funcionario_id"]
    ponto.empresa_id = request.form["empresa_id"]
    ponto.entrada1 = limpar_horario(request.form["entrada1"])
    ponto.saida1 = limpar_horario(request.form["saida1"])
    ponto.entrada2 = limpar_horario(request.form["entrada2"])
    ponto.saida2 = limpar_horario(request.form["saida2"])
    ponto.entrada3 = limpar_horario(request.form["entrada3"])
    ponto.saida3 = limpar_horario(request.form["saida3"])
    db.session.commit()
    flash("Registro atualizado com sucesso.")
    return redirect(request.referrer or url_for("registro"))


@app.route("/cadastro_empresa", methods=["GET", "POST"])
def cadastro_empresa():

    if not session.get("usuario_logado"):
        return redirect(url_for("login"))

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

    if not session.get("usuario_logado"):
        return redirect(url_for("login"))

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

    pontos = []
    if funcionario_id or empresa_id or data_ini or data_fim:
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

    
            

        ponto.horas_diurnas_reais = timedelta()
        ponto.horas_noturnas_reais = timedelta()
        ponto.horas_fictas = timedelta()
        ponto.horas_adicional = timedelta()
        ponto.horas_adicional_ficta = timedelta()
        ponto.horas_diurnas = timedelta()
        ponto.horas_noturnas = timedelta()
        ponto.horas_total = timedelta()
        ponto.extra_50_diurno = timedelta()
        ponto.extra_50_noturno = timedelta()
        ponto.extra_50_noturno_reais = timedelta()
        ponto.extra_100_diurno = timedelta()
        ponto.extra_100_noturno = timedelta()
        ponto.horas_normais = timedelta(hours=8)
        if ponto.data_obj.weekday() == 5:
            ponto.horas_normais = timedelta(hours=4)
    

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

        # Inicialização antes do loop
        acumulado_domingo = timedelta()

        
        duracao_dentro_domingo = timedelta()

        for minuto in minutos_marcados:
            hora = minuto.time()
            tipo = "diurna"
            if hora >= ININOT or hora < FIMNOT:
                tipo = "noturna"

            # DOMINGO (dia real do minuto)
            if ponto.data_obj.weekday() == 6:
                dia_real = minuto.weekday()

                if dia_real == 6:
                    if tipo == "diurna":
                        ponto.extra_100_diurno += timedelta(minutes=1)
                        ponto.horas_diurnas_reais += timedelta(minutes=1)
                    else:
                        ponto.extra_100_noturno += timedelta(minutes=1)
                        ponto.horas_noturnas_reais += timedelta(minutes=1)
                    duracao_dentro_domingo += timedelta(minutes=1)
                    continue

                elif dia_real == 0:
                    if duracao_dentro_domingo < timedelta(hours=8):
                        ponto.horas_normais += timedelta(minutes=1)
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
                    continue

            # SÁBADO virando domingo
            if ponto.data_obj.weekday() == 5 and minuto.date() > ponto.data_obj.date():
                if tipo == "diurna":
                    ponto.extra_100_diurno += timedelta(minutes=1)
                    ponto.horas_diurnas_reais += timedelta(minutes=1)
                else:
                    ponto.extra_100_noturno += timedelta(minutes=1)
                    ponto.horas_noturnas_reais += timedelta(minutes=1)
                continue

            # OUTROS DIAS OU RESTO
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


        # DIA DE SEMANA (Segunda a Sexta)
        if ponto.data_obj.weekday() < 5:
            ponto.horas_noturnas = ponto.horas_noturnas_reais * 1.142857
            ponto.horas_total = ponto.horas_diurnas_reais + ponto.horas_noturnas
            ponto.horas_fictas= ponto.horas_noturnas_reais * 0.142857
            carga_horaria_diaria = timedelta(hours=8)
            jornada_total = ponto.horas_diurnas_reais + ponto.horas_noturnas
            

            if jornada_total < carga_horaria_diaria:
                ponto.horas_normais = jornada_total
                
            else:
                ponto.horas_normais = carga_horaria_diaria
                ponto.extra_50_noturno = ( ponto.extra_50_noturno_reais * 1.142857 ) + ( ponto.horas_adicional * 0.142857 )
                
        # SÁBADO
        if ponto.data_obj.weekday() == 5:
            ponto.horas_noturnas = ponto.horas_noturnas_reais * 1.142857
            ponto.horas_total = ponto.horas_diurnas_reais + ponto.horas_noturnas
            ponto.horas_fictas= ponto.horas_noturnas_reais * 0.142857
            carga_horaria_diaria = timedelta(hours=4)
            jornada_total = ponto.horas_diurnas_reais + ponto.horas_noturnas
            extra_total = max(timedelta(), jornada_total - carga_horaria_diaria)
            ponto.extra_50_noturno = ponto.extra_50_noturno_reais * 1.142857

            if ponto.horas_adicional > timedelta():
                ponto.extra_50_noturno = ponto.horas_adicional * 0.142857

            if jornada_total < carga_horaria_diaria:
                ponto.horas_normais = jornada_total
                ponto.horas_adicional = ponto.horas_noturnas
            else:
                ponto.horas_normais = carga_horaria_diaria

        # DOMINGO
        if ponto.data_obj.weekday() == 6:
            ponto.horas_noturnas = ponto.horas_noturnas_reais * 1.142857
            ponto.horas_total = ponto.horas_diurnas_reais + ponto.horas_noturnas
            ponto.horas_fictas= ponto.horas_noturnas_reais * 0.142857
            carga_horaria_diaria = timedelta(hours=8)
            jornada_total = ponto.horas_diurnas_reais + ponto.horas_noturnas

            if jornada_total < carga_horaria_diaria:
                ponto.horas_normais = jornada_total
                    
            else:
                ponto.horas_normais = carga_horaria_diaria - (ponto.extra_100_diurno + ponto.extra_100_noturno)
                ponto.extra_50_noturno = ( ponto.extra_50_noturno_reais * 1.142857 ) + ( ponto.horas_adicional * 0.142857 )


    total = {
            "horas_diurnas": timedelta(),
            "horas_noturnas": timedelta(),
            "horas_fictas": timedelta(),
            "horas_total": timedelta(),
            "horas_normais": timedelta(),
            "horas_adicional": timedelta(),
            "extra_50_diurno": timedelta(),
            "extra_50_noturno": timedelta(),
            "extra_100_diurno": timedelta(),
            "extra_100_noturno": timedelta(),
        }

    for ponto in pontos:
            total["horas_diurnas"] += ponto.horas_diurnas_reais
            total["horas_noturnas"] += ponto.horas_noturnas
            total["horas_fictas"] += ponto.horas_fictas
            total["horas_total"] += ponto.horas_total
            total["horas_normais"] += ponto.horas_normais
            total["horas_adicional"] += ponto.horas_adicional
            total["extra_50_diurno"] += ponto.extra_50_diurno
            total["extra_50_noturno"] += ponto.extra_50_noturno
            total["extra_100_diurno"] += ponto.extra_100_diurno
            total["extra_100_noturno"] += ponto.extra_100_noturno


    return render_template("lista_registros.html", pontos=pontos, funcionarios=funcionarios, empresas=empresas, total=total)


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

    query = Ponto.query

    funcionario_id = request.args.get("funcionario_id")
    data_ini = request.args.get("data_ini")
    data_fim = request.args.get("data_fim")

    if funcionario_id:
        query = query.filter_by(funcionario_id=funcionario_id)
    if data_ini:
        query = query.filter(Ponto.data >= data_ini)
    if data_fim:
        query = query.filter(Ponto.data <= data_fim)

    pontos = []
    if request.args.get("data_ini") or request.args.get("data_fim") or request.args.get("funcionario_id"):
        pontos = query.order_by(Ponto.id.asc()).all()

    for ponto in pontos:
        if isinstance(ponto.data, str):
            ponto.data_obj = datetime.strptime(ponto.data, "%Y-%m-%d")
        else:
            ponto.data_obj = ponto.data

    return render_template("registro.html", funcionarios=funcionarios, empresas=empresas, pontos=pontos)


@app.template_filter('formatar_dia_semana')
def formatar_dia_semana(data):
    return format_datetime(data, "EEEE", locale='pt_BR').capitalize()

@app.route("/excluir_ponto/<int:id>")
def excluir_ponto(id):
    ponto = Ponto.query.get_or_404(id)
    db.session.delete(ponto)
    db.session.commit()
    return redirect(request.referrer or url_for("registro"))

@app.route("/excluir_funcionario/<int:id>")
def excluir_funcionario(id):
    funcionario = Funcionario.query.get_or_404(id)
    db.session.delete(funcionario)
    db.session.commit()
    return redirect(url_for("cadastro_funcionario"))

@app.route("/editar_funcionario/<int:id>", methods=["POST"])
def editar_funcionario(id):
    funcionario = Funcionario.query.get_or_404(id)
    funcionario.nome = request.form["nome"]
    funcionario.cpf = request.form["cpf"]
    db.session.commit()
    flash("Funcionário atualizado com sucesso.")
    return redirect(url_for("cadastro_funcionario"))

@app.route("/excluir_empresa/<int:id>")
def excluir_empresa(id):
    empresa = Empresa.query.get_or_404(id)
    db.session.delete(empresa)
    db.session.commit()
    return redirect(url_for("cadastro_empresa"))

@app.route("/editar_empresa/<int:id>", methods=["POST"])
def editar_empresa(id):
    empresa = Empresa.query.get_or_404(id)
    empresa.nome = request.form["nome"]
    empresa.vale_alimentacao = request.form["vale_alimentacao"]
    db.session.commit()
    flash("Empresa atualizada com sucesso.")
    return redirect(url_for("cadastro_empresa"))

@app.route("/importar", methods=["GET", "POST"])
def importar_csv():
    if not session.get("usuario_logado"):
        return redirect(url_for("login"))

    empresas = Empresa.query.order_by(Empresa.nome.asc()).all()

    if request.method == "POST":
        empresa_id = request.form["empresa_id"]
        arquivo = request.files.get("arquivo")

        if not arquivo or not arquivo.filename.endswith(".csv"):
            flash("Arquivo inválido. Envie um CSV.")
            return redirect(url_for("importar_csv"))

        from io import TextIOWrapper
        import csv

        def limpar_hora(valor):
            valor = valor.strip().strip("'")
            if not valor or "FERIADO" in valor.upper():
                return None
            return valor

        arquivo_stream = TextIOWrapper(arquivo, encoding="utf-8")
        leitor = csv.DictReader(arquivo_stream)

        for linha in leitor:
            nome = linha["'01 - NOME'"].strip().strip("'")
            def formatar_cpf(cpf_raw):
                cpf_raw = ''.join(filter(str.isdigit, cpf_raw))
                if len(cpf_raw) == 11:
                    return f"{cpf_raw[:3]}.{cpf_raw[3:6]}.{cpf_raw[6:9]}-{cpf_raw[9:]}"
                return cpf_raw

            cpf = formatar_cpf(linha["'02 - CPF'"].strip().strip("'"))
            data = linha["'03 - DIA / MÊS'"].strip().strip("'")

            entrada1 = limpar_hora(linha["'09 - TURNO 1 - INICIO'"])
            saida1   = limpar_hora(linha["'10 - TURNO 1 - FIM'"])
            entrada2 = limpar_hora(linha["'11 - TURNO 2 - INICIO'"])
            saida2   = limpar_hora(linha["'12 - TURNO 2 - FIM'"])
            entrada3 = limpar_hora(linha["'13 - TURNO 3 - INICIO'"])
            saida3   = limpar_hora(linha["'14 - TURNO 3 - FIM'"])

            # Ignorar se todos os campos estiverem vazios
            if not any([entrada1, saida1, entrada2, saida2, entrada3, saida3]):
                continue

            funcionario = Funcionario.query.filter_by(nome=nome).first()
            if not funcionario:
                funcionario = Funcionario(nome=nome, cpf=cpf)
                db.session.add(funcionario)
                db.session.commit()

            novo_ponto = Ponto(
                funcionario_id=funcionario.id,
                empresa_id=empresa_id,
                data=datetime.strptime(data, "%d/%m/%Y").date(),
                entrada1=entrada1,
                saida1=saida1,
                entrada2=entrada2,
                saida2=saida2,
                entrada3=entrada3,
                saida3=saida3
            )
            db.session.add(novo_ponto)

        db.session.commit()
        flash("Importação concluída com sucesso.")
        return redirect(url_for("registro"))

    return render_template("importar.html", empresas=empresas)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)



