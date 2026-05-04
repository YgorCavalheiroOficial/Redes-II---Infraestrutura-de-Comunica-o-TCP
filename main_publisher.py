from cliente.aplicacao_cliente import Cliente
import time

if __name__ == "__main__":
    # Instancia outro cliente e conecta ao Broker
    publicador = Cliente(broker_host='127.0.0.1', broker_port=1024)
    publicador.conectar()
    
    print("\n" + "="*30)
    print("MODO PUBLICADOR INICIADO")
    print("="*30)
    
    while True:
        topico = input("\nDigite o TÓPICO que deseja publicar (ou 'sair' para fechar): ")
        
        if topico.strip().lower() == 'sair':
            print("Encerrando publicador...")
            break
        mensagem = input(f"Digite a MENSAGEM para o tópico '{topico}': ")
        
        publicador.publicar(topico, mensagem)
        print("✅ Mensagem enviada para o Broker!")
        
        time.sleep(0.5)