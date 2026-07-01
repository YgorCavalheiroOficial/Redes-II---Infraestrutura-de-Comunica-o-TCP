import json
import os
import socket
import threading
import base64

from utils.crypto_utils import CryptoUtils
from utils.cert_utils import CertUtils
from utils.canal_seguro import CanalSeguro

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------- Interruptor PRODUÇÃO x TESTE (sem precisar editar código) ---------
# Defina a variável de ambiente USAR_AC_TESTE=1 antes de rodar para usar a
# Autoridade Certificadora FALSA local (pasta certificados_ac_teste/), gerada
# por 'ferramentas_teste/gerar_ambiente_teste.py'. Isso serve como plano B
# para apresentação/demo caso a AC real do professor ainda não tenha chegado.
# Sem a variável (ou com ela em 0), o projeto roda em modo produção normal,
# esperando os certificados reais em certificados_ac/.
USAR_AC_TESTE = os.environ.get("USAR_AC_TESTE", "0").strip().lower() in ("1", "true", "sim")
CERT_DIR = os.path.join(BASE_DIR, "certificados_ac_teste" if USAR_AC_TESTE else "certificados_ac")


class Broker:
    def __init__(self, host='127.0.0.1', port=1024,
                 caminho_cert_broker=None, caminho_chave_broker=None, caminho_cert_ca=None):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Estrutura permanente de tópicos: { 'topico': {'ID_Cliente1', 'ID_Cliente2'} }
        self.topicos = {}

        # Dicionário de mapeamento dinâmico: { 'ID_Cliente': CanalSeguro }
        self.clientes_online = {}

        # Certificados (PEM) dos clientes já autenticados, necessários para
        # que OUTROS clientes montem envelopes de criptografia ponta-a-ponta.
        self.certificados_clientes = {}

        # Buffer de Mensagens pendentes exigido na AV3
        # Estrutura: { 'topico': [ {'remetente': X, 'e2e': {cid: {...}}, 'pendentes': {...}}, ... ] }
        self.buffer_mensagens = {}

        # --------- Identidade do Broker (certificado assinado pela AC / professor) ---------
        caminho_cert_broker = caminho_cert_broker or os.path.join(CERT_DIR, "broker_cert.crt")
        caminho_chave_broker = caminho_chave_broker or os.path.join(CERT_DIR, "chave_privada_broker.pem")
        caminho_cert_ca = caminho_cert_ca or os.path.join(CERT_DIR, "certificado_ac.crt")

        if not (os.path.exists(caminho_cert_broker) and os.path.exists(caminho_chave_broker)):
            raise FileNotFoundError(
                "Certificado/chave do broker não encontrados.\n"
                f"  Esperado: {caminho_cert_broker}\n"
                f"            {caminho_chave_broker}\n"
                "Gere a requisição com 'certificados_ac/gerar_requisicao_broker.py', envie o "
                "arquivo broker.csr para o professor assinar e salve o .crt retornado com esse nome."
            )
        if not os.path.exists(caminho_cert_ca):
            raise FileNotFoundError(
                f"Certificado da AC (professor) não encontrado em '{caminho_cert_ca}'.\n"
                "Solicite ao professor o certificado público (.crt) da Autoridade Certificadora "
                "e salve-o nesse caminho."
            )

        self.cert_broker = CertUtils.carregar_certificado(caminho_cert_broker)
        self.chave_privada_broker = CertUtils.carregar_chave_privada(caminho_chave_broker)
        self.cert_ca = CertUtils.carregar_certificado(caminho_cert_ca)
        self.cert_broker_pem = CertUtils.cert_para_pem(self.cert_broker)

        # Sanidade: o próprio broker confia no seu certificado? (detecta configuração errada cedo)
        if not CertUtils.verificar_certificado(self.cert_broker, self.cert_ca):
            raise ValueError(
                "O certificado do broker NÃO foi assinado pela AC informada em 'certificado_ac.crt'. "
                "Confira se os arquivos não foram trocados."
            )

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        if USAR_AC_TESTE:
            print("⚠️  MODO TESTE: usando AC local FALSA (certificados_ac_teste/). "
                  "NÃO é a AC do professor.")
        print(f"Broker iniciado em {self.host}:{self.port} no aguardo de conexões TCP...")
        print(f"Identidade do broker: {CertUtils.obter_common_name(self.cert_broker)}")

        while True:
            conn, addr = self.server_socket.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()

    # ==========================================================================
    # HANDSHAKE DE SEGURANÇA (envelopamento digital + autenticação mútua)
    # ==========================================================================

    def _handshake_envelopamento(self, canal: CanalSeguro, addr) -> bool:
        """Etapa 2 do diagrama do enunciado: troca de certificado do broker e
        estabelecimento da chave de sessão simétrica via RSA (envelopamento)."""
        canal.enviar({'acao': 'SERVER_CERT', 'certificado': self.cert_broker_pem})

        pacote = canal.receber_um()
        if pacote.get('acao') != 'KEY_EXCHANGE':
            print(f"[{addr}] Handshake abortado: pacote inesperado ({pacote.get('acao')}).")
            return False

        try:
            chave_sessao = CryptoUtils.rsa_decrypt(
                self.chave_privada_broker, base64.b64decode(pacote['chave_sessao'])
            )
        except Exception as e:
            print(f"[{addr}] Falha ao decifrar chave de sessão: {e}")
            return False

        canal.enviar({'acao': 'SESSION_ESTABLISHED'})
        canal.definir_chave_sessao(chave_sessao)
        return True

    def _autenticar_cliente(self, canal: CanalSeguro, addr):
        """Autenticação do cliente: valida o certificado contra a AC e exige prova
        de posse da chave privada (assinatura de um desafio aleatório)."""
        pacote = canal.receber_um()
        if pacote.get('acao') != 'CLIENT_CERT':
            print(f"[{addr}] Handshake abortado: esperava CLIENT_CERT.")
            return None

        try:
            cert_cliente = CertUtils.pem_para_cert(pacote['certificado'])
        except Exception:
            canal.enviar({'acao': 'AUTH_FAIL', 'motivo': 'Certificado ilegível.'})
            return None

        if not CertUtils.verificar_certificado(cert_cliente, self.cert_ca):
            print(f"[{addr}] ❌ Certificado de cliente REJEITADO (assinatura inválida / AC não confiável).")
            canal.enviar({'acao': 'AUTH_FAIL', 'motivo': 'Certificado não assinado por uma AC confiável.'})
            return None

        if not CertUtils.certificado_valido_no_periodo(cert_cliente):
            print(f"[{addr}] ❌ Certificado de cliente EXPIRADO ou ainda não válido.")
            canal.enviar({'acao': 'AUTH_FAIL', 'motivo': 'Certificado fora do período de validade.'})
            return None

        # Prova de posse: desafio aleatório assinado com a chave privada do cliente
        nonce = os.urandom(32)
        canal.enviar({'acao': 'AUTH_CHALLENGE', 'nonce': base64.b64encode(nonce).decode()})

        resposta = canal.receber_um()
        if resposta.get('acao') != 'AUTH_RESPONSE':
            return None

        assinatura = base64.b64decode(resposta['assinatura'])
        chave_publica_cliente = CertUtils.obter_chave_publica(cert_cliente)
        print(f"[DEBUG-BROKER] Módulo da chave pública do CERTIFICADO recebido: {hex(chave_publica_cliente.public_numbers().n)[:50]}...")
        if not CryptoUtils.verificar_assinatura(chave_publica_cliente, assinatura, nonce):
            print(f"[{addr}] ❌ Falha na prova de posse da chave privada do cliente.")
            canal.enviar({'acao': 'AUTH_FAIL', 'motivo': 'Assinatura do desafio inválida.'})
            return None

        client_id = resposta.get('client_id') or CertUtils.obter_common_name(cert_cliente)
        self.certificados_clientes[client_id] = pacote['certificado']
        canal.enviar({'acao': 'AUTH_OK'})
        print(f"✅ Cliente autenticado com sucesso: {client_id}")
        return client_id

    # ==========================================================================
    # LOOP PRINCIPAL DE ATENDIMENTO
    # ==========================================================================

    def handle_client(self, conn, addr):
        print(f"Nova conexão TCP estabelecida de {addr}")
        canal = CanalSeguro(conn)
        client_id = None

        try:
            if not self._handshake_envelopamento(canal, addr):
                return

            client_id = self._autenticar_cliente(canal, addr)
            if not client_id:
                return

            self.clientes_online[client_id] = canal

            # Restaura sessão: tópicos aos quais o client_id já pertencia
            topicos_salvos = [t for t, membros in self.topicos.items() if client_id in membros]
            canal.enviar({'acao': 'CONNECT_ACK', 'topicos_restaurados': topicos_salvos})

            # Reenvia os certificados dos pares de cada tópico restaurado (necessário
            # para a criptografia ponta-a-ponta funcionar após reconexão)
            for topico in topicos_salvos:
                self._enviar_topic_peers(canal, topico, client_id)

            self.entregar_mensagens_pendentes(client_id)

            while True:
                dados = conn.recv(4096)
                if not dados:
                    break
                for comando in canal.receber_disponiveis(dados):
                    self._processar_comando(canal, client_id, comando)

        except ConnectionError as e:
            print(f"[{client_id or addr}] Conexão encerrada: {e}")
        except Exception as e:
            print(f"Erro no processamento do cliente {client_id or addr}: {e}")
        finally:
            if client_id in self.clientes_online:
                del self.clientes_online[client_id]
            print(f"Cliente '{client_id or addr}' ficou OFFLINE.")
            conn.close()

    def _processar_comando(self, canal, client_id, comando):
        acao = comando.get('acao')

        if acao == 'SUBSCRIBE':
            topico = comando['topico']
            if topico not in self.topicos:
                self.topicos[topico] = set()

            self._enviar_topic_peers(canal, topico, client_id)
            self.topicos[topico].add(client_id)
            print(f"Cliente '{client_id}' inscrito no tópico '{topico}'")

            # Avisa os membros já online do tópico que um novo par entrou
            # (para que eles também possam cifrar mensagens futuras para ele)
            for outro_id in self.topicos[topico]:
                if outro_id != client_id and outro_id in self.clientes_online:
                    self.clientes_online[outro_id].enviar({
                        'acao': 'PEER_JOINED',
                        'topico': topico,
                        'client_id': client_id,
                        'certificado': self.certificados_clientes.get(client_id)
                    })

        elif acao == 'UNSUBSCRIBE':
            topico = comando['topico']
            if topico in self.topicos and client_id in self.topicos[topico]:
                self.topicos[topico].remove(client_id)
                print(f"Cliente '{client_id}' removido do tópico '{topico}'")

        elif acao == 'PUBLISH':
            topico = comando['topico']
            e2e = comando.get('e2e', {})
            self.processar_publicacao(topico, e2e, remetente=client_id)

    def _enviar_topic_peers(self, canal, topico, client_id):
        """Envia ao cliente os certificados dos demais membros já inscritos no tópico,
        para que ele possa montar envelopes de criptografia ponta-a-ponta ao publicar."""
        membros = self.topicos.get(topico, set())
        peers = {
            cid: self.certificados_clientes[cid]
            for cid in membros
            if cid != client_id and cid in self.certificados_clientes
        }
        canal.enviar({'acao': 'TOPIC_PEERS', 'topico': topico, 'peers': peers})

    # ==========================================================================
    # ROTEAMENTO DE PUBLICAÇÕES (o broker NUNCA decifra o payload)
    # ==========================================================================

    def processar_publicacao(self, topico, e2e_map, remetente):
        inscritos = self.topicos.get(topico, set())
        # Só considera destinatários que: (a) estão inscritos e (b) o remetente
        # conseguiu montar um envelope para eles (isto é, tinha o certificado deles).
        destinatarios_pendentes = {cid for cid in inscritos if cid != remetente and cid in e2e_map}

        if not destinatarios_pendentes:
            print(f"[PUB] Sem destinatários válidos em '{topico}'. Mensagem descartada.")
            return

        nova_mensagem = {
            'remetente': remetente,
            'e2e': dict(e2e_map),                       # broker só enxerga blocos cifrados
            'pendentes': destinatarios_pendentes.copy()
        }

        if topico not in self.buffer_mensagens:
            self.buffer_mensagens[topico] = []
        self.buffer_mensagens[topico].append(nova_mensagem)

        for cid in list(destinatarios_pendentes):
            if cid in self.clientes_online:
                bloco_cifrado = nova_mensagem['e2e'][cid]
                if self.enviar_mensagem_direta(cid, topico, bloco_cifrado, remetente):
                    nova_mensagem['pendentes'].remove(cid)

        if not nova_mensagem['pendentes']:
            self.buffer_mensagens[topico].remove(nova_mensagem)

    def enviar_mensagem_direta(self, client_id, topico, bloco_e2e, remetente):
        try:
            canal_destino = self.clientes_online[client_id]
            canal_destino.enviar({
                'acao': 'RECEIVE',
                'topico': topico,
                'remetente': remetente,
                'e2e_para_mim': bloco_e2e   # {'chave': b64, 'dados': b64} -> opaco para o broker
            })
            return True
        except Exception:
            return False

    def entregar_mensagens_pendentes(self, client_id):
        """ Varre o buffer entregando o histórico acumulado enquanto o cliente estava fora """
        for topico, lista_mensagens in list(self.buffer_mensagens.items()):
            for msg in list(lista_mensagens):
                if client_id in msg['pendentes']:
                    bloco_e2e = msg['e2e'].get(client_id)
                    if bloco_e2e and self.enviar_mensagem_direta(client_id, topico, bloco_e2e, msg['remetente']):
                        msg['pendentes'].remove(client_id)
                        print(f"[BUFFER -> {client_id}] Mensagem antiga de '{msg['remetente']}' descarregada.")

                        if not msg['pendentes']:
                            lista_mensagens.remove(msg)