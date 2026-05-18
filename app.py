from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import os # IMPORTAÇÃO ADICIONADA PARA LIDAR COM PASTAS
from werkzeug.utils import secure_filename # IMPORTAÇÃO ADICIONADA PARA NOME DE ARQUIVOS

app = Flask(__name__)
app.secret_key = 'chave_secreta_projeto_final'

# --- CONFIGURAÇÃO DE UPLOAD DE FOTOS ---
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Cria a pasta static/uploads automaticamente se ela não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 

# 1. BANCO DE DADOS 
usuarios_db = {
    'admin': {
        'nome': 'Administrador', 
        'senha': '123', 
        'cargo': 'admin', 
        'email': 'admin@teste.com',
        'permissoes': ['dashboard', 'relatorios', 'usuarios_gestao', 'permissoes', 'perfil'],
        'foto': 'https://i.pravatar.cc/150?img=11' 
    },
    'teste': {
        'nome': 'Usuario Teste', 
        'senha': '123', 
        'cargo': 'user', 
        'email': 'teste@teste.com',
        'permissoes': ['dashboard', 'perfil'],
        'foto': 'https://i.pravatar.cc/150?img=12' 
    }
}

logs_atividade = []

# 2. FUNÇÃO AUXILIAR PARA LOGS E SEGURANÇA
def registrar_log(usuario, acao):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    logs_atividade.append({"usuario": usuario, "acao": acao, "data_hora": agora})

def tem_permissao(p):
    """ Verifica se o usuário logado tem uma permissão específica """
    if 'usuario' not in session:
        return False
    
    user = usuarios_db.get(session['usuario'])
    
    # Trava de segurança: se o usuário não for encontrado (ex: servidor reiniciou), nega a permissão
    if user is None:
        session.pop('usuario', None) 
        return False
        
    return p in user.get('permissoes', [])

# 3. ROTAS DE ACESSO
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
    return render_template('perfil.html', usuario=dados)

# 5. ADMINISTRAÇÃO 
@app.route('/relatorios')
def relatorios():
    if not tem_permissao('relatorios'):
        return "Acesso negado aos Relatórios!", 403
    
    logs_filtrados = [log for log in logs_atividade if log['usuario'] != 'admin']
    return render_template('relatorios.html', logs=logs_filtrados)

@app.route('/usuarios_gestao')
def usuarios_gestao():
    if not tem_permissao('usuarios_gestao'):
        return "Acesso negado à Gestão de Usuários!", 403
        
    return render_template('usuarios.html', lista=usuarios_db)

@app.route('/permissoes', methods=['GET', 'POST'])
def permissoes():
    if not tem_permissao('permissoes'):
        return "Acesso negado à configuração de permissões!", 403

    usuario_logado = usuarios_db.get(session['usuario'])

    if request.method == 'POST':
        usuario_alvo = request.form.get('usuario_alvo')
        novas_permissoes = request.form.getlist('permissoes_selecionadas')
        
        if usuario_alvo in usuarios_db:
            if usuario_alvo == session['usuario'] and 'permissoes' not in novas_permissoes:
                return "Erro: Você não pode remover sua própria permissão de acesso à esta aba!"

            usuarios_db[usuario_alvo]['permissoes'] = novas_permissoes
            registrar_log(session['usuario'], f"Alterou permissões de {usuario_alvo} para {novas_permissoes}")
            
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

    if request.method == 'POST':
        usuarios_db[username]['nome'] = request.form.get('nome')
        usuarios_db[username]['email'] = request.form.get('email')
        usuarios_db[username]['senha'] = request.form.get('senha')
        usuarios_db[username]['foto'] = request.form.get('foto', usuarios_db[username].get('foto'))
        return redirect(url_for('usuarios_gestao'))

    return render_template('editar.html', u=usuarios_db[username], username=username)

if __name__ == '__main__':
    app.run(debug=True)