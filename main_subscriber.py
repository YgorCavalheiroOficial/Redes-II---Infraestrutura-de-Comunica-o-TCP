from cliente.aplicacao_cliente import Cliente
import time

if __name__ == "__main__":
    # Instancia um cliente e conecta ao Broker
    inscrito = Cliente(broker_host='127.0.0.1', broker_port=5000)
    inscrito.conectar()
    
    # Informa ao Broker que quer receber mensagens do Tópico A
    inscrito.inscrever("Topico A")
    
    print("Inscrito no 'Topico A'. Aguardando mensagens...")
    
    # Mantém o script rodando para a thread de escuta continuar ativa
    while True:
        time.sleep(1)