from cliente.aplicacao_cliente import Cliente
import time

if __name__ == "__main__":
    # Instancia outro cliente e conecta ao Broker
    publicador = Cliente(broker_host='127.0.0.1', broker_port=5000)
    publicador.conectar()
    
    # Publica uma mensagem no mesmo tópico
    print("Enviando mensagem secreta para o 'Topico A'...")
    publicador.publicar("Topico A", "Olá! Esta é uma mensagem confidencial ponta a ponta.")
    
    # Aguarda um pouco antes de encerrar
    time.sleep(2)