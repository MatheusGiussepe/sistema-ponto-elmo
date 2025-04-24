from extensoes import db

class Funcionario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)

class Empresa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    vale_alimentacao = db.Column(db.Float, nullable=False)

class Ponto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    data = db.Column(db.String(10), nullable=False)
    entrada1 = db.Column(db.String(5))
    saida1 = db.Column(db.String(5))
    entrada2 = db.Column(db.String(5))
    saida2 = db.Column(db.String(5))
    entrada3 = db.Column(db.String(5))
    saida3 = db.Column(db.String(5))

    funcionario = db.relationship('Funcionario', backref=db.backref('pontos', lazy=True))
    empresa = db.relationship('Empresa', backref=db.backref('pontos', lazy=True))
