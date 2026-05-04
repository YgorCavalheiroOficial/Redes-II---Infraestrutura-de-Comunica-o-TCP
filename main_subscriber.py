from cliente.aplicacao_cliente import Cliente
import time

if __name__ == "__main__":
    inscrito = Cliente(broker_host='127.0.0.1', broker_port=1024)
    inscrito.conectar()
    
    print("\n" + "="*30)
    print("MODO ASSINANTE INICIADO")
    print("="*30)
    
    while True:
        topico = input("\nDigite o TÓPICO que deseja se inscrever (ou 'sair' para fechar): ")
        
        if topico.strip().lower() == 'sair':
            print("Encerrando assinante...")
            break
            
        inscrito.inscrever(topico)
        print(f"✅ Inscrição enviada! Agora você receberá mensagens do tópico '{topico}'.")