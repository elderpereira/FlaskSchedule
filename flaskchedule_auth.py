from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import schedule
import threading
import time
import subprocess
import csv
import os
import datetime

# Lista de comandos perigosos
COMANDOS_PERIGOSOS = [
    'os.remove', 'shutil.rmtree', 'subprocess.run(["rm', 'subprocess.run(["del'
]

################

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ua_chave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/create_account', methods=['GET', 'POST'])
@login_required
def create_account():
    print("Entrou no create_account")
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Usuário já existe.')
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('Conta criada com sucesso.')
            return redirect(url_for('index'))
    return render_template('create_account.html')

@app.route('/edit_account/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_account(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        db.session.commit()
        return redirect(url_for('list_accounts'))
    return render_template('edit_account.html', user=user)

@app.route('/delete_account/<int:user_id>', methods=['POST'])
@login_required
def delete_account(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('list_accounts'))

@app.route('/list_accounts')
@login_required
def list_accounts():
    users = User.query.all()
    return render_template('list_accounts.html', users=users)

###############

tarefas_agendadas = set()

def carregar_tarefas():
    print("Carregando tarefas...")
    tarefas = []
    if os.path.exists('bd.csv'):
        with open('bd.csv', mode='r', newline='', encoding='utf-8') as arquivo:
            leitor = csv.DictReader(arquivo)
            for linha in leitor:
                print(f"Tarefa carregada: {linha['caminho_script']}")
                tarefas.append(linha)
                intervalo = linha.get('intervalo')
                if intervalo:
                    intervalo = int(intervalo)
                else:
                    intervalo = 1  # Valor padrão caso intervalo não esteja presente
                print(f"Agendando tarefa: {linha['nome']} com intervalo: {intervalo}")
                agendar_tarefa(linha['nome'], linha['caminho_script'], linha['horario'], linha['frequencia'], intervalo)
    return tarefas

def salvar_tarefas(tarefas):
    print("Salvando tarefas...")
    campos = ['nome', 'caminho_script', 'horario', 'frequencia', 'intervalo']
    
    if not os.path.exists('bd.csv'):
        with open('bd.csv', mode='w', newline='', encoding='utf-8') as arquivo:
            escritor = csv.DictWriter(arquivo, fieldnames=campos)
            escritor.writeheader()
    
    with open('bd.csv', mode='w', newline='', encoding='utf-8') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        for tarefa in tarefas:
            escritor.writerow(tarefa)

def executar_script(nome, caminho_script):
    print(f"Executando o script: {nome}")
    try:
        # Construir o caminho completo do script
        caminho_completo_script = os.path.join('Scripts', caminho_script)
        
        inicio = datetime.datetime.now()
        result = subprocess.run(["python", caminho_completo_script], capture_output=True, text=True, check=True)
        fim = datetime.datetime.now()
        
        if result.returncode == 0:
            print(f"Script {caminho_completo_script} executado com sucesso.")
            saida = result.stdout
        else:
            print(f"Erro ao executar o script: {result.stderr}")
            saida = result.stderr
        
        registrar_log(nome, caminho_completo_script, inicio, fim, saida, "Agendado")
        
    except subprocess.CalledProcessError as e:
        fim = datetime.datetime.now()
        saida = str(e)
        registrar_log(nome, caminho_completo_script, inicio, fim, saida, "Agendado")
        print(f"Erro ao executar o script: {e}")

def agendar_tarefa(nome, caminho_script, horario, frequencia, intervalo=1):
    if nome in tarefas_agendadas:
        print(f"Tarefa {nome} já está agendada.")
        return

    print(f"Iniciando agendando da tarefa: {nome} - {caminho_script}")
    print(f"Parâmetros recebidos - Nome: {nome}, Horário: {horario}, Frequência: {frequencia}, Intervalo: {intervalo}")
    try:
        print("Entrou no bloco try")
        print(f"Agendando a tarefa: {nome} - {caminho_script} - Frequência: {frequencia}")
        if frequencia == 'diaria':
            print(f"Entrou no if diaria")
            print(f"Tarefa agendada: {nome} - {caminho_script} - Hora de execução: {horario} - A cada: {intervalo} Dias")
            schedule.every(intervalo).days.at(horario).do(executar_script, nome=nome, caminho_script=caminho_script)
        elif frequencia == 'semanal':
            print(f"Entrou no elif semanal")
            schedule.every(intervalo).weeks.at(horario).do(executar_script, nome=nome, caminho_script=caminho_script)
            print(f"Tarefa agendada: {nome} - {caminho_script} - Hora de execução: {horario} - A cada: {intervalo} Semanas")
        elif frequencia == 'horaria':
            print(f"Entrou no elif horaria")
            schedule.every(intervalo).hours.do(executar_script, nome=nome, caminho_script=caminho_script)
            print(f"Tarefa agendada: {nome} - {caminho_script} - A cada: {intervalo} Horas")
        elif frequencia == 'minutos':
            print(f"Entrou no elif minutos")
            print(f"Tarefa agendada: {nome} - {caminho_script} - A cada: {intervalo} Minutos")
            schedule.every(intervalo).minutes.do(executar_script, nome=nome, caminho_script=caminho_script)
        else:
            print("Nenhuma condição foi atendida")
        tarefas_agendadas.add(nome)
    except ValueError as e:
        print(f"Erro ao agendar a tarefa: {e}")
        pass  # Ignora erros de agendamento aqui, pois já foram tratados na adição
    print("Saiu do bloco try")

def agendar_tarefas():
    while True:
        print("Verificando.......")
        schedule.run_pending()
        time.sleep(10)
        carregar_tarefas()

def registrar_log(nome, nome_tarefa, inicio, fim, saida, modo):
    print(f"Registrando log da tarefa: {nome_tarefa}")
    log_file = 'execucao_log.csv'
    file_exists = os.path.isfile(log_file)
    
    with open(log_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            # Escrever cabeçalhos se o arquivo não existir
            writer.writerow(['Tarefa', 'Script', 'Início', 'Fim', 'Saída', 'Modo'])
        
        writer.writerow([nome, nome_tarefa, inicio, fim, saida, modo])


@app.route('/executar/<caminho_script>', methods=['POST'])
@login_required
def executar_tarefa(caminho_script):
    try:
        nome = request.args.get('nome')
        
        # Construir o caminho completo do script na pasta Scripts
        caminho_completo_script = os.path.join('Scripts', caminho_script)
        
        print(f"Tentando executar o script: {caminho_completo_script}")
        
        inicio = datetime.datetime.now()
        result = subprocess.run(["python", caminho_completo_script], capture_output=True, text=True)
        fim = datetime.datetime.now()
        
        if result.returncode == 0:
            print(f"Script {caminho_completo_script} executado com sucesso.")
            saida = result.stdout
        else:
            print(f"Erro ao executar o script: {result.stderr}")
            saida = result.stderr
        
        registrar_log(nome, caminho_completo_script, inicio, fim, saida, "Manual")
        
        return redirect(url_for('index'))
    except subprocess.CalledProcessError as e:
        fim = datetime.datetime.now()
        saida = str(e)
        registrar_log(nome, caminho_completo_script, inicio, fim, saida, "Manual")
        print(f"Erro ao executar o script: {e}")
        return redirect(url_for('index'))

@app.route('/')
@login_required
def index():
    tarefas = carregar_tarefas()
    
    # Listar arquivos .py na pasta Scripts
    pasta_scripts = 'Scripts'
    arquivos_scripts = [f for f in os.listdir(pasta_scripts) if f.endswith('.py')]
    
    return render_template('index.html', tarefas=tarefas, arquivos_scripts=arquivos_scripts)

@app.route('/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar():
    tarefas = carregar_tarefas()
    
    # Listar arquivos .py na pasta Scripts
    pasta_scripts = 'Scripts'
    arquivos_scripts = [f for f in os.listdir(pasta_scripts) if f.endswith('.py')]
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        caminho_script = request.form.get('caminho_script')
        horario = request.form.get('horario')
        frequencia = request.form.get('frequencia')
        intervalo = request.form.get('intervalo', type=int)  # Captura o valor de intervalo como inteiro
        
        if not (nome and caminho_script and horario and frequencia and intervalo):
            return "Todos os campos são obrigatórios", 400
        
        tarefas.append({'nome': nome, 'caminho_script': caminho_script, 'horario': horario, 'frequencia': frequencia, 'intervalo': intervalo})
        agendar_tarefa(caminho_script, horario, frequencia, intervalo)
        salvar_tarefas(tarefas)
        return redirect(url_for('index'))
    
    return render_template('adicionar.html', arquivos_scripts=arquivos_scripts)

@app.route('/editar/<nome>', methods=['GET', 'POST'])
@login_required
def editar(nome):
    tarefas = carregar_tarefas()
    tarefa_editar = next((tarefa for tarefa in tarefas if tarefa['nome'] == nome), None)
    
    # Listar arquivos .py na pasta Scripts
    pasta_scripts = 'Scripts'
    arquivos_scripts = [f for f in os.listdir(pasta_scripts) if f.endswith('.py')]
    
    if request.method == 'POST':
        if tarefa_editar:
            tarefa_editar['caminho_script'] = request.form.get('caminho_script')
            tarefa_editar['horario'] = request.form.get('horario')
            tarefa_editar['frequencia'] = request.form.get('frequencia')
            tarefa_editar['intervalo'] = request.form.get('intervalo', type=int)  # Captura o valor de intervalo como inteiro
            salvar_tarefas(tarefas)
            return redirect(url_for('index'))
    if not tarefa_editar:
        return redirect(url_for('index'))
    return render_template('editar.html', tarefa=tarefa_editar, arquivos_scripts=arquivos_scripts)

@app.route('/excluir/<nome>', methods=['POST'])
@login_required
def excluir(nome):
    tarefas = carregar_tarefas()
    tarefas = [tarefa for tarefa in tarefas if tarefa['nome'] != nome]
    salvar_tarefas(tarefas)
    return redirect(url_for('index'))


# Rota para criar um novo script
@app.route('/criar_script', methods=['GET', 'POST'])
@login_required
def criar_script():
    if request.method == 'POST':
        nome_script = request.form.get('nome_script')
        conteudo_script = request.form.get('conteudo_script').replace('\r\n', '\n')  # Normaliza as quebras de linha
        caminho_script = os.path.join('Scripts', f'{nome_script}')
        
        with open(caminho_script, 'w', newline='') as file:
            file.write(conteudo_script)
        
        return redirect(url_for('index'))
    
    return render_template('criar_script.html')

# Rota para editar um script existente
@app.route('/editar_script/<nome_script>', methods=['GET', 'POST'])
@login_required
def editar_script(nome_script):
    caminho_script = os.path.join('Scripts', f'{nome_script}')
    
    if request.method == 'POST':
        conteudo_script = request.form.get('conteudo_script').replace('\r\n', '\n')  # Normaliza as quebras de linha
        
        with open(caminho_script, 'w', newline='') as file:
            file.write(conteudo_script)
        
        return redirect(url_for('index'))
    
    with open(caminho_script, 'r') as file:
        conteudo_script = file.read()
    
    return render_template('editar_script.html', nome_script=nome_script, conteudo_script=conteudo_script)

@app.route('/relatorio')
@login_required
def relatorio():
    print("Gerando relatório...")
    caminho_logs = ('execucao_log.csv')  # Ajuste o caminho para o arquivo de logs

    logs = []
    if os.path.exists(caminho_logs):
        with open(caminho_logs, newline='', encoding='utf-8') as csvfile:
            print("Arquivo de logs encontrado")
            reader = csv.DictReader(csvfile)
            for row in reader:
                logs.append(row)
    else:
        logs.append({"Tarefa": "Nenhum log encontrado", "Início": "", "Fim": "", "Saída": "", "Modo": ""})

    return render_template('relatorio.html', logs=logs)

@app.route('/excluir_script/<nome_script>', methods=['POST'])
@login_required
def excluir_script(nome_script):
    caminho_script = os.path.join('Scripts', f'{nome_script}')
    
    if os.path.exists(caminho_script):
        os.remove(caminho_script)
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists('users.db'):
        with app.app_context():
            db.create_all()
            # existing_user = User.query.filter_by(username='admin').first()
            # if not existing_user:
            #     new_user = User(username='admin', password='admin')
            #     db.session.add(new_user)
            #     db.session.commit()
    tarefas = carregar_tarefas()
    thread = threading.Thread(target=agendar_tarefas, daemon=True)
    thread.start()
    debug = False
    app.run(debug=True, host='0.0.0.0', port=777)
