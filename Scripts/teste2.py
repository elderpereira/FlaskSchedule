from datetime import datetime

def imprimir_hora_atual():
    agora = datetime.now()
    hora_formatada = agora.strftime('%Y-%m-%d %H:%M:%S')
    print(f"Hora atual: {hora_formatada}")

if __name__ == "__main__":
    imprimir_hora_atual()

print("Script executado")
print("Script executado")