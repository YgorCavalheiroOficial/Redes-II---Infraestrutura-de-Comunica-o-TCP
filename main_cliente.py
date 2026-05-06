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
        modo = input("\nO que deseja fazer? (PUB / SUB / UNSUB / SAIR): ").strip().lower()

        if modo == 'unsub':
            if not cliente.topicos_inscritos:
                print("❌ Você não está inscrito em nenhum tópico no momento.")
                continue
                
            print(f"Tópicos atuais: {list(cliente.topicos_inscritos)}")
            topico = input("Digite o TÓPICO que deseja cancelar a inscrição: ").strip()
            cliente.desinscrever(topico)

        elif modo == 'sub':
            topico = input("\nDigite o TÓPICO que deseja se inscrever: ").strip()
            if topico.lower() == 'sair':
                break

            cliente.inscrever(topico)
            print(f"✅ Inscrição enviada! Agora você receberá mensagens do tópico '{topico}'.")
            print(f"\nTópicos atuais: {list(cliente.topicos_inscritos)}.")

        elif modo == 'pub':
            if not cliente.topicos_inscritos:
                print("\n" + "!"*45)
                print("❌ ACESSO NEGADO: Você não pode publicar.")
                print("Você deve estar inscrito em ao menos UM tópico.")
                print("!"*45)
                continue

            topico = input("\nDigite o TÓPICO que deseja publicar: ").strip()
        
            if topico not in cliente.topicos_inscritos:
                print("❌ ACESSO NEGADO: Você não pode publicar em um tópico que não está inscrito.")
                continue

            mensagem = input(f"Digite a MENSAGEM para o tópico '{topico}': ").strip()
        
            cliente.publicar(topico, mensagem)
            print("✅ Mensagem enviada para o Broker!")

            time.sleep(0.5)

        elif modo == 'sair':
            print("Encerrando o Client...")
            break

        else:
            print("❌ Opção inválida. Por favor, digite PUB, SUB, UNSUB ou SAIR.")