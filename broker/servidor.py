import json
import socket
import threading
from utils.crypto_utils import CryptoUtils

class Broker:
    def __init__(self, host='127.0.0.1', port=1024):
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
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()

    def handle_client(self, conn, addr):
        print(f"Novo cliente conectado: {addr}")
        buffer = ""
        
        try:
            while True: 
                data = conn.recv(2048)
                if not data: 
                    print(f"Conexão encerrada pelo cliente {addr}")
                    break
                    
                buffer += data.decode()
                mensagens = buffer.split('\n')
                buffer = mensagens.pop()
                
                for msg_str in mensagens:
                    if not msg_str.strip(): 
                        continue
                    
                    # Tenta ler o JSON. Se der erro, ignora a sujeira e continua vivo
                    try:
                        comando = json.loads(msg_str)
                    except json.JSONDecodeError:
                        print(f"Ignorando lixo não-JSON recebido de {addr}: {msg_str}")
                        continue
                    
                    if comando['acao'] == 'SUBSCRIBE':
                        topico = comando['topico']
                        if topico not in self.topicos:
                            self.topicos[topico] = []
                        self.topicos[topico].append(conn)
                        print(f"Cliente {addr} inscrito no {topico}")
                        
                    elif comando['acao'] == 'PUBLISH':
                        topico = comando['topico']
                        payload = comando['payload']
                        print(f"Mensagem recebida no tópico '{topico}': {payload}")
                        self.notificar_inscritos(topico, payload, remetente=conn)

        except Exception as e:
            print(f"Erro na conexão com {addr}: {e}")
        finally:
            # Limpeza
            for topico, clientes in self.topicos.items():
                if conn in clientes:
                    clientes.remove(conn)
            conn.close()

    def notificar_inscritos(self, topico, payload, remetente):
        print(f"\n[DEBUG] Iniciando notificação para o tópico: '{topico}'")
        print(f"[DEBUG] Tópicos que existem na memória agora: {list(self.topicos.keys())}")
        
        if topico in self.topicos:
            print(f"[DEBUG] Tópico '{topico}' encontrado! Total de inscritos: {len(self.topicos[topico])}")
            mensagem = (json.dumps({
                'acao': 'RECEIVE',
                'topico': topico,
                'payload': payload
            }) + "\n").encode()
            
            for cliente in self.topicos[topico]:
                print(f"[DEBUG] Analisando cliente...")
                if cliente != remetente:
                    try:
                        cliente.send(mensagem)
                        print("[DEBUG] -> Mensagem ENVIADA com sucesso ao Subscriber!")
                    except Exception as e:
                        print(f"[DEBUG] -> FALHA ao enviar para Subscriber: {e}")
                        self.topicos[topico].remove(cliente)
                else:
                    print("[DEBUG] -> Este cliente é o Publisher (remetente). A regra impede de devolver a mensagem para ele mesmo.")
        else:
            print(f"[DEBUG] O tópico '{topico}' não tem ninguém inscrito. Mensagem descartada.")