import json
import socket

class Cliente:
    def __init__(self, broker_host='127.0.0.1', broker_port=1024):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.topicos_inscritos = set() 

    def conectar(self, client_id):
        self.socket.connect((self.broker_host, self.broker_port))
        
        # Envia o pacote de identificação única no início
        pacote = json.dumps({
            'acao': 'CONNECT',
            'client_id': client_id
        }) + "\n"
        self.socket.send(pacote.encode())

    def inscrever(self, topico):
        self.topicos_inscritos.add(topico)
        pacote = json.dumps({
            'acao': 'SUBSCRIBE',
            'topico': topico
        }) + "\n"
        self.socket.send(pacote.encode())

    def desinscrever(self, topico):
        if topico in self.topicos_inscritos:
            self.topicos_inscritos.remove(topico)
        pacote = json.dumps({
            'acao': 'UNSUBSCRIBE',
            'topico': topico
        }) + "\n"
        self.socket.send(pacote.encode())

    def publicar(self, topico, mensagem_clara):
        pacote = json.dumps({
            'acao': 'PUBLISH', 
            'topico': topico, 
            'payload': mensagem_clara
        }) + "\n"
        self.socket.send(pacote.encode())

    def escutar(self, callback=None):
        buffer = "" 
        while True:
            try:
                data = self.socket.recv(2048)
                if not data:
                    print("Conexão com o Broker foi encerrada.")
                    break
                
                buffer += data.decode()
                
                while "\n" in buffer:
                    msg_str, buffer = buffer.split("\n", 1)
                    if not msg_str.strip(): continue
                    
                    pacote = json.loads(msg_str)

                    # 🆕 NOVO: Trata o retorno de restauração de sessão do Broker
                    if pacote['acao'] == 'CONNECT_ACK':
                        topicos_recuperados = pacote.get('topicos_restaurados', [])
                        for topico in topicos_recuperados:
                            self.topicos_inscritos.add(topico)
                        
                        # Envia uma mensagem especial de SISTEMA para o feed do chat atualizar a interface
                        if callback:
                            callback("SISTEMA", f"Sessão restaurada! Suas inscrições ativas foram recuperadas: {', '.join(topicos_recuperados)}", "BROKER")
                        continue
                    
                    if pacote['acao'] == 'RECEIVE':
                        topico = pacote['topico']
                        mensagem = pacote['payload']
                        remetente = pacote.get('remetente', 'Desconhecido')
                        
                        if callback:
                            # 🔴 CORREÇÃO: Passa de forma posicional (tópico, mensagem, remetente)
                            # garantindo que case perfeitamente com a assinatura da GUI
                            callback(topico, mensagem, remetente)
                        else:
                            print(f"\n[{remetente} em '{topico}']: {mensagem}")
                        
            except Exception as e:
                print(f"Erro na escuta: {e}")
                break