import json
import socket
import threading
from utils.crypto_utils import CryptoUtils

class Broker:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        
        # Configuração do Socket TCP (IPv4, Stream/TCP)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Dicionário para gerenciar tópicos e inscritos { 'Topic A': [conn1, conn2] }
        self.topicos = {}  
       
        # Chaves do Broker para implementação da criptografia nas próximas entregas
        self.chave_privada, self.chave_publica = CryptoUtils.gerar_par_chaves()
        
    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Broker iniciado em {self.host}:{self.port} no aguardo de conexões TCP...")
        
        while True:
            conn, addr = self.server_socket.accept()
            # Inicia uma thread para cada cliente conectado
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()

    def handle_client(self, conn, addr):
        print(f"Novo cliente conectado: {addr}")
        buffer = ""
        
        try:
            # Passo 1: Apresentação do cliente
            msg_inicial = conn.recv(1024).decode()
            if msg_inicial == "HELLO_BROKER":
                conn.send("HELLO_CLIENT".encode())

            # Passo 2 & 3: Handshake, Envelopamento e Autenticação para a próxima entrega
            # print(f"Realizando Handshake e validando assinaturas com {addr}...")
            
            # Loop principal para ler as mensagens
            while True:
                data = conn.recv(2048)
                if not data:
                    break # Ocorre quando o cliente desconecta.
                
                # TCP Stream: junta os pedaços e separa por quebra de linha
                buffer += data.decode()
                mensagens = buffer.splint('\n')

                # O último elemento é sempre vazio ou incompleto, volta pro buffer
                buffer = mensagens.pop()
                
                for msg_str in mensagens:
                    if not msg_str.strip(): continue

                    comando = json.loads(msg_str)
                    
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
                        payload = comando['payload']
                        # O Broker apenas repassa o payload, não consegue ler o conteúdo
                        print(f"Repassando pacote cifrado ponta a ponta no '{topico}': {payload}...")
                        self.notificar_inscritos(topico, payload, remetente=conn)

        except Exception as e:
            print(f"Erro na conexão com {addr}: {e}")
        finally:
            # Limpeza caso o cliente desconecte
            for topico, clientes in self.topicos.items():
                if conn in clientes:
                    clientes.remove(conn)
            conn.close()

    def notificar_inscritos(self, topico, payload, remetente):
        if topico in self.topicos:
            mensagem = json.dumps({
                'acao': 'RECEIVE',
                'topico': topico,
                'payload': payload
            }) +"\n".encode()
            
            for cliente in self.topicos[topico]:
                if cliente != remetente: # Não envia de volta para quem publicou
                    try:
                        cliente.send(mensagem)
                    except:
                        self.topicos[topico].remove(cliente)