from flask import Flask, render_template, request, redirect, session, url_for
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'chave_secreta_projeto_final'

usuarios_db = {
    "admin": {"senha": "123", "nome": "Administrador", "email": "admin@sistema.com", "cargo": "admin"}
}
logs_atividade = []

def registrar_log(usuario, acao):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    logs_atividade.append({"usuario": usuario, "acao": acao, "data_hora": agora})

@app.route('/')
def home():
    if 'usuario' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form.get('usuario')
        senha_input = request.form.get('senha')
        if user_input in usuarios_db and usuarios_db[user_input]['senha'] == senha_input:
            session['usuario'] = user_input
            registrar_log(user_input, "Fez login")
            return redirect(url_for('dashboard'))
        return "Erro! <a href='/login'>Voltar</a>"
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        user = request.form.get('usuario')
        usuarios_db[user] = {"senha": request.form.get('senha'), "nome": request.form.get('nome'), "email": request.form.get('email'), "cargo": "comum"}
        registrar_log(user, "Criou conta")
        return redirect(url_for('login'))
    return render_template('cadastro.html')

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html', user=usuarios_db[session['usuario']])

@app.route('/relatorios')
def relatorios():
    if session.get('usuario') != 'admin': return "Acesso negado!"
    logs_filtrados = [log for log in logs_atividade if log['usuario'] != 'admin']
    return render_template('relatorios.html', logs=logs_filtrados)

@app.route('/usuarios_gestao')
def usuarios_gestao():
    if session.get('usuario') != 'admin': return "Acesso negado!"
    return render_template('usuarios.html', lista=usuarios_db)

@app.route('/excluir/<username>')
def excluir(username):
    if session.get('usuario') == 'admin' and username != 'admin':
        usuarios_db.pop(username, None)
    return redirect(url_for('usuarios_gestao'))

@app.route('/editar/<username>', methods=['GET', 'POST'])
def editar(username):
    if session.get('usuario') != 'admin': return "Acesso negado!"
    if request.method == 'POST':
        usuarios_db[username]['nome'] = request.form.get('nome')
        usuarios_db[username]['email'] = request.form.get('email')
        usuarios_db[username]['senha'] = request.form.get('senha')
        return redirect(url_for('usuarios_gestao'))
    return render_template('editar.html', u=usuarios_db[username], username=username)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)