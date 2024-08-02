from flask import Flask, request, render_template, redirect, url_for
import schedule
import threading
import time
import subprocess
import csv
import os
import datetime

app = Flask(__name__)

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
                print(f"Agendando tarefa: {linha['caminho_script']} com intervalo: {intervalo}")
                agendar_tarefa(linha['caminho_script'], linha['horario'], linha['frequencia'], intervalo)
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

def executar_script(caminho_script):
    print(f"Executando o script: {caminho_script}")
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
        
        registrar_log(caminho_script, inicio, fim, saida, "Agendado")
        
    except subprocess.CalledProcessError as e:
        fim = datetime.datetime.now()
        saida = str(e)
        registrar_log(caminho_script, inicio, fim, saida, "Agendado")
        print(f"Erro ao executar o script: {e}")

def agendar_tarefa(caminho_script, horario, frequencia, intervalo=1):
    print(f"Iniciando agendando da tarefa: {caminho_script}")
    print(f"Parâmetros recebidos - Horário: {horario}, Frequência: {frequencia}, Intervalo: {intervalo}")
    try:
        print("Entrou no bloco try")
        print(f"Agendando a tarefa: {caminho_script} - Frequência: {frequencia}")
        if frequencia == 'diaria':
            print(f"Entrou no if diaria")
            print(f"Tarefa agendada: {caminho_script} - Hora de execução: {horario} - A cada: {intervalo} Dias")
            schedule.every(intervalo).days.at(horario).do(executar_script, caminho_script=caminho_script)
        elif frequencia == 'semanal':
            print(f"Entrou no elif semanal")
            schedule.every(intervalo).weeks.at(horario).do(executar_script, caminho_script=caminho_script)
            print(f"Tarefa agendada: {caminho_script} - Hora de execução: {horario} - A cada: {intervalo} Semanas")
        elif frequencia == 'horaria':
            print(f"Entrou no elif horaria")
            schedule.every(intervalo).hours.do(executar_script, caminho_script=caminho_script)
            print(f"Tarefa agendada: {caminho_script} - A cada: {intervalo} Horas")
        elif frequencia == 'minutos':
            print(f"Entrou no elif minutos")
            print(f"Tarefa agendada: {caminho_script} - A cada: {intervalo} Minutos")
            schedule.every(intervalo).minutes.do(executar_script, caminho_script=caminho_script)
        else:
            print("Nenhuma condição foi atendida")
    except ValueError as e:
        print(f"Erro ao agendar a tarefa: {e}")
        pass  # Ignora erros de agendamento aqui, pois já foram tratados na adição
    print("Saiu do bloco try")

def agendar_tarefas():
    while True:
        print("Verificando.......")
        schedule.run_pending()
        time.sleep(10)

def registrar_log(nome_tarefa, inicio, fim, saida, modo):
    print(f"Registrando log da tarefa: {nome_tarefa}")
    log_file = 'execucao_log.csv'
    file_exists = os.path.isfile(log_file)
    
    with open(log_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            # Escrever cabeçalhos se o arquivo não existir
            writer.writerow(['Tarefa', 'Início', 'Fim', 'Saída', 'Modo'])
        
        writer.writerow([nome_tarefa, inicio, fim, saida, modo])


@app.route('/executar/<nome_tarefa>', methods=['POST'])
def executar_tarefa(nome_tarefa):
    try:
        caminho_script = os.path.join('Scripts', nome_tarefa)
        print(f"Tentando executar o script: {caminho_script}")
        
        inicio = datetime.datetime.now()
        result = subprocess.run(["python", caminho_script], capture_output=True, text=True)
        fim = datetime.datetime.now()
        
        if result.returncode == 0:
            print(f"Script {caminho_script} executado com sucesso.")
            saida = result.stdout
        else:
            print(f"Erro ao executar o script: {result.stderr}")
            saida = result.stderr
        
        registrar_log(nome_tarefa, inicio, fim, saida, "Manual")
        
        return redirect(url_for('index'))
    except subprocess.CalledProcessError as e:
        fim = datetime.datetime.now()
        saida = str(e)
        registrar_log(nome_tarefa, inicio, fim, saida, "Manual")
        print(f"Erro ao executar o script: {e}")
        return redirect(url_for('index'))

@app.route('/')
def index():
    tarefas = carregar_tarefas()
    
    # Listar arquivos .py na pasta Scripts
    pasta_scripts = 'Scripts'
    arquivos_scripts = [f for f in os.listdir(pasta_scripts) if f.endswith('.py')]
    
    return render_template('index.html', tarefas=tarefas, arquivos_scripts=arquivos_scripts)

@app.route('/adicionar', methods=['GET', 'POST'])
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
def excluir(nome):
    tarefas = carregar_tarefas()
    tarefas = [tarefa for tarefa in tarefas if tarefa['nome'] != nome]
    salvar_tarefas(tarefas)
    return redirect(url_for('index'))


# Rota para criar um novo script
@app.route('/criar_script', methods=['GET', 'POST'])
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

@app.route('/excluir_script/<nome_script>', methods=['POST'])
def excluir_script(nome_script):
    caminho_script = os.path.join('Scripts', f'{nome_script}')
    
    if os.path.exists(caminho_script):
        os.remove(caminho_script)
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    tarefas = carregar_tarefas()
    thread = threading.Thread(target=agendar_tarefas, daemon=True)
    thread.start()
    app.run(debug=True, host='0.0.0.0', port=777)
    subprocess.run(["pip", "install", "gunicorn"])
