import json
import socket
import threading
from utils.crypto_utils import CryptoUtils

class Broker:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.topicos = {}  # Passo 4: Dicionário para gerenciar tópicos e inscritos { 'Topic A': [conn1, conn2] }
        
        # Chaves do Broker
        self.chave_privada, self.chave_publica = CryptoUtils.gerar_par_chaves()
        
    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Broker iniciado em {self.host}:{self.port} no aguardo de conexões TCP...")
        
        while True:
            conn, addr = self.server_socket.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()

    def handle_client(self, conn, addr):
        print(f"Nova conexão TCP (Passo 1): {addr}")
        
        try:
            # Passo 1: Recebimento do "Olá" inicial
            msg_inicial = conn.recv(1024).decode()
            if msg_inicial == "HELLO_BROKER":
                conn.send("HELLO_CLIENT".encode())

            # Passo 2 & 3: Handshake, Envelopamento e Autenticação (Simplificado no modelo)
            # Na prática real, você trocaria chaves públicas, validaria o certificado do cliente e receberia a chave simétrica cifrada.
            print(f"Realizando Handshake e validando assinaturas com {addr}...")
            
            # Loop principal de recebimento de comandos do cliente
            while True:
                data = conn.recv(2048)
                if not data:
                    break
                
                # Assume-se que a mensagem aqui já foi decifrada com a chave simétrica do envelopamento
                comando = json.loads(data.decode())
                
                # Passo 4: Lógica de Tópicos
                if comando['acao'] == 'SUBSCRIBE':
                    topico = comando['topico']
                    if topico not in self.topicos:
                        self.topicos[topico] = []
                    self.topicos[topico].append(conn)
                    print(f"Cliente {addr} inscrito no {topico}")
                    
                # Passo 5: Confidencialidade Ponta a Ponta
                elif comando['acao'] == 'PUBLISH':
                    topico = comando['topico']
                    payload_cifrado = comando['payload_cifrado']
                    # O Broker apenas repassa o payload_cifrado, não consegue ler o conteúdo
                    print(f"Repassando pacote cifrado ponta a ponta no {topico}...")
                    self.notificar_inscritos(topico, payload_cifrado, remetente=conn)

        except Exception as e:
            print(f"Erro na conexão com {addr}: {e}")
        finally:
            conn.close()

    def notificar_inscritos(self, topico, payload_cifrado, remetente):
        if topico in self.topicos:
            mensagem = json.dumps({
                'acao': 'RECEIVE',
                'topico': topico,
                'payload_cifrado': payload_cifrado
            }).encode()
            
            for cliente in self.topicos[topico]:
                if cliente != remetente: # Não envia de volta para quem publicou
                    try:
                        cliente.send(mensagem)
                    except:
                        self.topicos[topico].remove(cliente)