import socket
from utils.crypto_utils import CryptoUtils


def __init__(self, host='127.0.0.1', port=1024):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Agora o dicionário armazena STRINGS com IDs dos clientes: { 'carros': {'cliente_1', 'cliente_2'} }
        self.topicos = {}  
       
        # NOVIDADE 1: Controla quais clientes fixos estão com conexão ativa no momento { 'cliente_1': conn }
        self.clientes_online = {}

        # NOVIDADE 2: Buffer de Mensagens da AV3
        # Estrutura: { 'topico_A': [ {'remetente': 'X', 'payload': '...', 'pendentes': {'Y', 'Z'}}, ... ] }
        self.buffer_mensagens = {}

        self.chave_privada, self.chave_publica = CryptoUtils.gerar_par_chaves()