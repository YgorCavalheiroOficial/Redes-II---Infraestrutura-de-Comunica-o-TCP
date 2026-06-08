import json
import socket
import threading
from utils.crypto_utils import CryptoUtils

class Broker:
    def __init__(self, host='127.0.0.1', port=1024):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Estrutura permanente de tópicos: { 'topico': {'ID_Cliente1', 'ID_Cliente2'} }
        self.topicos = {}  
       
        # Dicionário de mapeamento dinâmico: { 'ID_Cliente': socket_connection }
        self.clientes_online = {}

        # Buffer de Mensagens pendentes exigido na AV3
        # Estrutura: { 'topico': [ {'remetente': 'X', 'payload': '...', 'pendentes': {'Y'}}, ... ] }
        self.buffer_mensagens = {}

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
        print(f"Nova conexão TCP estabelecida de {addr}")
        buffer = ""
        client_id = None
        
        try:
            while True:
                # 🔴 CORREÇÃO DO BUG: O recv deve ficar dentro do loop principal para sempre escutar dados
                data = conn.recv(2048)
                if not data: 
                    break
                
                buffer += data.decode()
                
                # Divisão correta e segura do fluxo de dados por quebra de linha (\n)
                while "\n" in buffer:
                    msg_str, buffer = buffer.split("\n", 1)
                    msg_str = msg_str.strip()
                    if not msg_str: continue
                    
                    # Mantém compatibilidade com saudações simples
                    if msg_str == "HELLO_BROKER":
                        conn.send("HELLO_CLIENT\n".encode())
                        continue
                    
                    comando = json.loads(msg_str)
                    
                    # --- REQUISITO AV3: IDENTIFICAÇÃO E REGISTRO DO CLIENTE ---
                    if comando['acao'] == 'CONNECT':
                        client_id = comando['client_id']
                        self.clientes_online[client_id] = conn
                        print(f"✅ Cliente identificado com sucesso: {client_id}")
                        
                        # 🆕 NOVO: Busca na memória do Broker quais tópicos este ID já pertencia
                        topicos_salvos = [topico for topico, inscritos in self.topicos.items() if client_id in inscritos]
                        
                        # Envia uma confirmação de conexão de volta informando os tópicos restaurados
                        resposta_connect = json.dumps({
                            'acao': 'CONNECT_ACK',
                            'topicos_restaurados': topicos_salvos
                        }) + "\n"
                        conn.send(resposta_connect.encode())
                        
                        # Ao conectar, verifica se há mensagens guardadas no buffer para ele
                        self.entregar_mensagens_pendentes(client_id)
                        
                    elif comando['acao'] == 'SUBSCRIBE':
                        if not client_id: continue
                        topico = comando['topico']
                        if topico not in self.topicos:
                            self.topicos[topico] = set()
                        self.topicos[topico].add(client_id) # Vincula o ID estável, não o socket temporário
                        print(f"Cliente '{client_id}' inscrito no tópico '{topico}'")
                        
                    elif comando['acao'] == 'UNSUBSCRIBE':
                        if not client_id: continue
                        topico = comando['topico']
                        if topico in self.topicos and client_id in self.topicos[topico]:
                            self.topicos[topico].remove(client_id)
                            print(f"Cliente '{client_id}' removido do tópico '{topico}'")
                            
                    # --- REQUISITO AV3: ENVIAR COM REMETENTE + TRATAR BUFFER ---
                    elif comando['acao'] == 'PUBLISH':
                        if not client_id: continue
                        topico = comando['topico']
                        payload = comando['payload']
                        self.processar_publicacao(topico, payload, remetente=client_id)

        except Exception as e:
            print(f"Erro no processamento do cliente {client_id or addr}: {e}")
        finally:
            if client_id in self.clientes_online:
                del self.clientes_online[client_id]
            print(f"Cliente '{client_id or addr}' ficou OFFLINE.")
            conn.close()

    def processar_publicacao(self, topico, payload, remetente):
        inscritos = self.topicos.get(topico, set())
        destinatarios_pendentes = {cid for cid in inscritos if cid != remetente}
        
        if not destinatarios_pendentes:
            print(f"[PUB] Sem outros inscritos em '{topico}'. Mensagem descartada.")
            return

        # Monta a estrutura de persistência temporária
        nova_mensagem = {
            'remetente': remetente,
            'payload': payload,
            'pendentes': destinatarios_pendentes.copy()
        }

        if topico not in self.buffer_mensagens:
            self.buffer_mensagens[topico] = []
        self.buffer_mensagens[topico].append(nova_mensagem)

        # Tenta enviar em tempo real para quem está ativo agora
        for cid in list(destinatarios_pendentes):
            if cid in self.clientes_online:
                conn_destino = self.clientes_online[cid]
                if self.enviar_mensagem_direta(conn_destino, topico, payload, remetente):
                    nova_mensagem['pendentes'].remove(cid)

        # Se todos receberam imediatamente, remove do buffer
        if not nova_mensagem['pendentes']:
            self.buffer_mensagens[topico].remove(nova_mensagem)

    def enviar_mensagem_direta(self, conn, topico, payload, remetente):
        try:
            # Envia a mensagem com a Origem bem definida (Requisito Crítico)
            pacote = json.dumps({
                'acao': 'RECEIVE',
                'topico': topico,
                'payload': payload,
                'remetente': remetente 
            }) + "\n"
            conn.send(pacote.encode())
            return True
        except:
            return False

    def entregar_mensagens_pendentes(self, client_id):
        """ Varre o buffer entregando o histórico acumulado enquanto o cliente estava fora """
        for topico, lista_mensagens in list(self.buffer_mensagens.items()):
            for msg in list(lista_mensagens):
                if client_id in msg['pendentes']:
                    conn = self.clientes_online[client_id]
                    if self.enviar_mensagem_direta(conn, topico, msg['payload'], msg['remetente']):
                        msg['pendentes'].remove(client_id)
                        print(f"[BUFFER -> {client_id}] Mensagem antiga de '{msg['remetente']}' descarregada.")
                        
                        if not msg['pendentes']:
                            lista_mensagens.remove(msg)