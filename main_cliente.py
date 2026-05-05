from cliente.aplicacao_cliente import Cliente
import time
import threading

if __name__ == "__main__":
    cliente = Cliente(broker_host='127.0.0.1', broker_port=1024)
    cliente.conectar()
    
    #Iniciação de uma thread de escuta
    thread_escuta = threading.Thread(target=cliente.escutar, daemon=True)
    thread_escuta.start()

    print("\n" + "="*30)
    print("MODO CLIENT ATIVADO")
    print("="*30)
    
    while True:
        modo = input("\nO que deseja fazer? (PUB / SUB / SAIR): ").strip().lower()

        if modo == 'sub':
            topico = input("\nDigite o TÓPICO que deseja se inscrever: ").strip()
            if topico.lower() == 'sair':
                break

            cliente.inscrever(topico)
            print(f"✅ Inscrição enviada! Agora você receberá mensagens do tópico '{topico}'.")

        elif modo == 'pub':
            topico = input("\nDigite o TÓPICO que deseja publicar: ").strip()
        
            mensagem = input(f"Digite a MENSAGEM para o tópico '{topico}': ").strip()
        
            cliente.publicar(topico, mensagem)
            print("✅ Mensagem enviada para o Broker!")

            time.sleep(0.5)

        elif modo == 'sair':
            print("Encerrando publicador...")
            break

        else:
            print("❌ Opção inválida. Por favor, digite PUB, SUB ou SAIR.")