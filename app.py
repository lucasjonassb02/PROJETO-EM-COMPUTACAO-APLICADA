from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import os 
from werkzeug.utils import secure_filename 

app = Flask(__name__)
app.secret_key = 'chave_secreta_projeto_final'

# --- CONFIGURAÇÃO DE UPLOAD DE FOTOS ---
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 

# 1. BANCO DE DADOS (Unificado com Tema e Foto de Perfil)
usuarios_db = {
    'admin': {
        'nome': 'Administrador', 
        'senha': '123', 
        'cargo': 'admin', 
        'email': 'admin@teste.com',
        'tema': 'light',
        'permissoes': ['dashboard', 'relatorios', 'usuarios_gestao', 'permissoes', 'perfil'],
        'foto': 'https://i.pravatar.cc/150?img=11' 
    },
    'teste': {
        'nome': 'Usuario Teste', 
        'senha': '123', 
        'cargo': 'user', 
        'email': 'teste@teste.com',
        'tema': 'light',
        'permissoes': ['dashboard', 'perfil'],
        'foto': 'https://i.pravatar.cc/150?img=12' 
    }
}

logs_atividade = []

def registrar_log(usuario, acao):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    logs_atividade.append({"usuario": usuario, "acao": acao, "data_hora": agora})

def tem_permissao(p):
    if 'usuario' not in session:
        return False
    
    user = usuarios_db.get(session['usuario'])
    
    if user is None:
        session.pop('usuario', None) 
        return False
        
    return p in user.get('permissoes', [])

@app.route('/')
def home():
    if 'usuario' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        user_input = request.form.get('usuario')
        senha_input = request.form.get('senha')
        if user_input in usuarios_db and usuarios_db[user_input]['senha'] == senha_input:
            session['usuario'] = user_input
            registrar_log(user_input, "Fez login")
            return redirect(url_for('dashboard'))
        
        erro = "Usuário ou senha incorretos."
        
    return render_template('login.html', erro=erro)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        user = request.form.get('usuario')
        usuarios_db[user] = {
            "senha": request.form.get('senha'), 
            "nome": request.form.get('nome'),
            "email": request.form.get('email'), 
            "cargo": "user",
            "tema": "light",
            "permissoes": ['dashboard', 'perfil'], 
            "foto": "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png"
        }
        registrar_log(user, "Criou conta")
        return redirect(url_for('login'))
    return render_template('cadastro.html')

@app.route('/logout')
def logout():
    registrar_log(session.get('usuario'), "Fez logout")
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/mudar_tema', methods=['POST'])
def mudar_tema():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    novo_tema = request.form.get('tema')
    username = session['usuario']
    if username in usuarios_db:
        usuarios_db[username]['tema'] = novo_tema
    return redirect(request.referrer or url_for('dashboard'))

# 4. PAINEL E PERFIL 
@app.route('/dashboard')
def dashboard():
    if not tem_permissao('dashboard'):
        return redirect(url_for('login'))
    usuario_dados = usuarios_db.get(session['usuario'])
    return render_template('dashboard.html', user=usuario_dados)

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if not tem_permissao('perfil'):
        return "Acesso negado ao Perfil!", 403
        
    username_logado = session['usuario']
    
    # SE O USUÁRIO ENVIOU UMA FOTO NOVA:
    if request.method == 'POST':
        if 'foto_nova' in request.files:
            arquivo = request.files['foto_nova']
            
            if arquivo.filename != '':
                nome_seguro = secure_filename(arquivo.filename)
                caminho_salvo = os.path.join(app.config['UPLOAD_FOLDER'], nome_seguro)
                arquivo.save(caminho_salvo)
                usuarios_db[username_logado]['foto'] = f'/{caminho_salvo}'
                
                registrar_log(username_logado, "Atualizou a foto de perfil")
                
    dados = usuarios_db.get(username_logado)
    # Mudado de "usuario=dados" para "user=dados" para casar com o perfil.html
    return render_template('perfil.html', user=dados)

# 5. ADMINISTRAÇÃO 
@app.route('/relatorios')
def relatorios():
    if not tem_permissao('relatorios'):
        return "Acesso negado!", 403
    usuario_dados = usuarios_db.get(session['usuario'])
    logs_filtrados = [log for log in logs_atividade if log['usuario'] != 'admin']
    return render_template('relatorios.html', logs=logs_filtrados, user=usuario_dados)

@app.route('/usuarios_gestao')
def usuarios_gestao():
    if not tem_permissao('usuarios_gestao'):
        return "Acesso negado!", 403
    usuario_dados = usuarios_db.get(session['usuario'])
    return render_template('usuarios.html', lista=usuarios_db, user=usuario_dados)

@app.route('/permissoes', methods=['GET', 'POST'])
def permissoes():
    if not tem_permissao('permissoes'):
        return "Acesso negado!", 403
    usuario_logado = usuarios_db.get(session['usuario'])
    if request.method == 'POST':
        usuario_alvo = request.form.get('usuario_alvo')
        novas_permissoes = request.form.getlist('permissoes_selecionadas')
        if usuario_alvo in usuarios_db:
            if usuario_alvo == session['usuario'] and 'permissoes' not in novas_permissoes:
                return "Erro: Não pode remover a sua própria permissão de administrador!"
            usuarios_db[usuario_alvo]['permissoes'] = novas_permissoes
    return render_template('permissoes.html', usuarios=usuarios_db, user=usuario_logado)

# 6. EDIÇÃO E EXCLUSÃO 
@app.route('/excluir/<username>')
def excluir(username):
    if tem_permissao('usuarios_gestao') and username != 'admin':
        usuarios_db.pop(username, None)
    return redirect(url_for('usuarios_gestao'))

@app.route('/editar/<username>', methods=['GET', 'POST'])
def editar(username):
    if not tem_permissao('usuarios_gestao'):
        return "Acesso negado!", 403
    usuario_dados = usuarios_db.get(session['usuario'])
    if request.method == 'POST':
        usuarios_db[username]['nome'] = request.form.get('nome')
        usuarios_db[username]['email'] = request.form.get('email')
        usuarios_db[username]['senha'] = request.form.get('senha')
        usuarios_db[username]['foto'] = request.form.get('foto', usuarios_db[username].get('foto'))
        return redirect(url_for('usuarios_gestao'))
    return render_template('editar.html', u=usuarios_db[username], username=username, user=usuario_dados)

if __name__ == '__main__':
    app.run(debug=True)