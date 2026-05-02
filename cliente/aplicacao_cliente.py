import json
import socket
import threading
from utils.crypto_utils import CryptoUtils

class Cliente:
    def __init__(self, broker_host='127.0.0.1', broker_port=5000):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Chaves do Cliente
        self.chave_privada, self.chave_publica = CryptoUtils.gerar_par_chaves()
        self.chave_simetrica_envelopamento = CryptoUtils.gerar_chave_simetrica()
        
        # Chave para Criptografia Ponta a Ponta (Compartilhada apenas entre clientes previamente)
        # Em um cenário real, você faria a troca de chaves E2E usando Diffie-Hellman ou similar.
        self.chave_e2e = Fernet(Fernet.generate_key()) 

    def conectar(self):
        # Passo 1: Conexão TCP Básica
        self.socket.connect((self.broker_host, self.broker_port))
        self.socket.send("HELLO_BROKER".encode())
        resposta = self.socket.recv(1024).decode()
        print(f"Resposta do servidor: {resposta}")
        
        # Passo 2 & 3: Aqui ocorreria a troca da chave_simetrica_envelopamento 
        # cifrada com a chave pública do Broker (Envelopamento Digital) e o envio
        # do certificado assinado pelo Broker para autenticação.
        
        # Inicia thread para escutar mensagens do Broker
        threading.Thread(target=self.escutar, daemon=True).start()

    def inscrever(self, topico):
        # Passo 4: Solicitação de entrada em um tópico
        msg = json.dumps({'acao': 'SUBSCRIBE', 'topico': topico})
        # Esta mensagem deveria ser cifrada com a chave simétrica do envelopamento antes do envio
        self.socket.send(msg.encode())

    def publicar(self, topico, mensagem_clara):
        # Passo 5: Confidencialidade Ponta a Ponta
        # Cifra o payload antes de colocar no pacote do Broker
        payload_cifrado = self.chave_e2e.encrypt(mensagem_clara.encode()).decode()
        
        msg = json.dumps({
            'acao': 'PUBLISH', 
            'topico': topico, 
            'payload_cifrado': payload_cifrado
        })
        # O cabeçalho ('acao', 'topico') fica visível para o Broker fazer o roteamento, 
        # mas o 'payload_cifrado' é ilegível para ele.
        self.socket.send(msg.encode())

    def escutar(self):
        while True:
            try:
                data = self.socket.recv(2048)
                if data:
                    pacote = json.loads(data.decode())
                    if pacote['acao'] == 'RECEIVE':
                        # Decifra o pacote ponta a ponta
                        payload_cifrado = pacote['payload_cifrado'].encode()
                        try:
                            msg_decifrada = self.chave_e2e.decrypt(payload_cifrado).decode()
                            print(f"\n[Mensagem Recebida no {pacote['topico']}] (Descriptografada): {msg_decifrada}")
                        except Exception:
                            print("\n[Erro] Falha ao decifrar mensagem E2E. Chaves não correspondem.")
            except Exception as e:
                print("Conexão encerrada.")
                break