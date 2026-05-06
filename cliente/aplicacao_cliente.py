import json
import socket
import threading
from utils.crypto_utils import CryptoUtils
from cryptography.fernet import Fernet

class Cliente:
    def __init__(self, broker_host='127.0.0.1', broker_port=1024):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Geração das chaves do cliente: pré estruturado para a implementação da criptografia para as próximas entregas
        #self.chave_privada, self.chave_publica = CryptoUtils.gerar_par_chaves()
        #self.chave_simetrica_envelopamento = CryptoUtils.gerar_chave_simetrica()
        # Chave para Criptografia Ponta a Ponta Compartilhada apenas entre clientes previamente
        #self.chave_e2e = Fernet(Fernet.generate_key()) 

        # Lista de tópicos que este cliente assinou
        self.topicos_inscritos = set()

    def conectar(self):
        #Conexão TCP Básica
        self.socket.connect((self.broker_host, self.broker_port))
        
        print(f"Conectado!")
        
        # Passo 2 & 3: Local destinado para realizar a troca da chave_simetrica_envelopamento para as próximas entregas
        # cifrada com a chave pública do Broker (Envelopamento Digital) e o envio do certificado assinado pelo Broker para autenticação.
        
        # Inicia thread para escutar mensagens do Broker
        threading.Thread(target=self.escutar, daemon=True).start()

    def inscrever(self, topico):
        self.topicos_inscritos.add(topico)

        #Solicitação de entrada em um tópico
        pacote = json.dumps({'acao': 'SUBSCRIBE', 'topico': topico}) + "\n"
        # Futuramente esta mensagem será cifrada com a chave simétrica do envelopamento antes do envio
        self.socket.send(pacote.encode())

        print(f"Inscrito em: {self.topicos_inscritos}")

    def desinscrever(self, topico):
        if topico in self.topicos_inscritos:
    
            self.topicos_inscritos.remove(topico)
            
            # 2. Prepara o pacote para o Broker
            pacote = json.dumps({
                'acao': 'UNSUBSCRIBE',
                'topico': topico
            }) + "\n"
            
            self.socket.send(pacote.encode())
            print(f"Desinscrição do tópico '{topico}' enviada ao servidor.")
        else:
            print(f"⚠️ Você não está inscrito no tópico '{topico}'.")

    def publicar(self, topico, mensagem_clara):
        # Passo 5: Futuramente será implementada a Confidencialidade Ponta a Ponta
        # Cifra o payload antes de colocar no pacote do Broker
        #payload_cifrado = self.chave_e2e.encrypt(mensagem_clara.encode()).decode()
        
        pacote = json.dumps({'acao': 'PUBLISH', 'topico': topico, 'payload': mensagem_clara}) + "\n"
        
        self.socket.send(pacote.encode())
        print ("*pacote enviado*")

    def escutar(self):
        buffer = "" 
        while True:
            try:
                data = self.socket.recv(2048)
                if not data:
                    print("Data vazio, mensagem não recebida")
                    print("Conexão com o Broker foi encerrada.")
                    break
                
                # Lida com o TCP Stream da mesma forma que o servidor
                buffer += data.decode()
                mensagens = buffer.split('\n')
                buffer = mensagens.pop()
                
                for msg_str in mensagens:
                    if not msg_str.strip(): continue
                    
                    pacote = json.loads(msg_str)
                    
                    if pacote['acao'] == 'RECEIVE':
                        # ADAPTAÇÃO FUTURA: em breve será usado o self.chave_e2e.decrypt() para decodificar a mensagem previamente criptografada.
                        topico = pacote['topico']
                        mensagem = pacote['payload']
                        print(f"\n[Nova Mensagem no tópico '{topico}']: {mensagem}")
                        
            except Exception as e:
                print(f"Erro na escuta: {e}")
                break