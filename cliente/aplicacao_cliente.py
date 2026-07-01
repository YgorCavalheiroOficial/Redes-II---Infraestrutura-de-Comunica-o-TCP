import json
import os
import socket
import base64

from utils.crypto_utils import CryptoUtils
from utils.cert_utils import CertUtils
from utils.canal_seguro import CanalSeguro

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------- Interruptor PRODUÇÃO x TESTE (sem precisar editar código) ---------
# Mesmo interruptor usado em broker/servidor.py — ver comentário lá para
# detalhes. Defina USAR_AC_TESTE=1 no ambiente para usar a AC local FALSA.
USAR_AC_TESTE = os.environ.get("USAR_AC_TESTE", "0").strip().lower() in ("1", "true", "sim")
CERT_DIR = os.path.join(BASE_DIR, "certificados_ac_teste" if USAR_AC_TESTE else "certificados_ac")
_NOME_CERT_CLIENTE_PADRAO = "certificado_cliente.crt"


class Cliente:
    def __init__(self, broker_host='127.0.0.1', broker_port=1024,
                 caminho_cert_cliente=None, caminho_chave_cliente=None, caminho_cert_ca=None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.canal = None

        self.topicos_inscritos = set()
        self.client_id = None

        # { topico: {client_id: x509.Certificate} } -> pares conhecidos, usados
        # para montar envelopes de criptografia ponta-a-ponta ao publicar
        self.peers_por_topico = {}

        # --------- Identidade do cliente (certificado assinado pela AC / professor) ---------
        caminho_cert_cliente = caminho_cert_cliente or os.path.join(
            CERT_DIR, _NOME_CERT_CLIENTE_PADRAO)
        caminho_chave_cliente = caminho_chave_cliente or os.path.join(
            CERT_DIR, "chave_privada_cliente.pem")
        caminho_cert_ca = caminho_cert_ca or os.path.join(CERT_DIR, "certificado_ac.crt")

        if not (os.path.exists(caminho_cert_cliente) and os.path.exists(caminho_chave_cliente)):
            raise FileNotFoundError(
                f"Certificado/chave do cliente não encontrados em '{CERT_DIR}'. "
                "Rode 'certificados_ac/gerar_requisicao.py' e peça ao professor para assinar o CSR."
            )
        if not os.path.exists(caminho_cert_ca):
            raise FileNotFoundError(
                f"Certificado da AC (professor) não encontrado em '{caminho_cert_ca}'. "
                "Solicite ao professor o certificado público (.crt) da Autoridade Certificadora."
            )

        self.cert_cliente = CertUtils.carregar_certificado(caminho_cert_cliente)
        self.chave_privada = CertUtils.carregar_chave_privada(caminho_chave_cliente)
        self.cert_ca = CertUtils.carregar_certificado(caminho_cert_ca)
        self.cert_cliente_pem = CertUtils.cert_para_pem(self.cert_cliente)

        print(f"[DEBUG-CLIENTE] Carregando certificado de: {caminho_cert_cliente}")
        print(f"[DEBUG-CLIENTE] Carregando chave privada de: {caminho_chave_cliente}")
        print(f"[DEBUG-CLIENTE] Módulo da chave pública DENTRO DO CERTIFICADO: {hex(self.cert_cliente.public_key().public_numbers().n)[:50]}...")
        print(f"[DEBUG-CLIENTE] Módulo derivado da CHAVE PRIVADA carregada:    {hex(self.chave_privada.public_key().public_numbers().n)[:50]}...")

    # ==========================================================================
    # CONEXÃO E HANDSHAKE DE SEGURANÇA
    # ==========================================================================

    def conectar(self, client_id):
        if USAR_AC_TESTE:
            print("⚠️  MODO TESTE: usando AC local FALSA (certificados_ac_teste/). "
                  "NÃO é a AC do professor.")
        self.socket.connect((self.broker_host, self.broker_port))
        self.canal = CanalSeguro(self.socket)

        self._handshake_envelopamento()
        self._autenticar(client_id)

        self.client_id = client_id

    def _handshake_envelopamento(self):
        """Recebe e valida o certificado do broker; em seguida gera uma chave de
        sessão simétrica e a envia protegida pela chave pública do broker (RSA)."""
        pacote = self.canal.receber_um()
        if pacote.get('acao') != 'SERVER_CERT':
            raise ConnectionError("Handshake inválido: broker não enviou seu certificado.")

        cert_broker = CertUtils.pem_para_cert(pacote['certificado'])

        # --- AUTENTICAÇÃO DO BROKER (requisito crítico) ---
        if not CertUtils.verificar_certificado(cert_broker, self.cert_ca):
            raise ConnectionError(
                "🚫 Certificado do broker NÃO foi assinado pela AC confiável. "
                "Conexão abortada (possível ataque man-in-the-middle)."
            )
        if not CertUtils.certificado_valido_no_periodo(cert_broker):
            raise ConnectionError("🚫 Certificado do broker está expirado ou ainda não é válido.")

        print(f"🔒 Broker autenticado com sucesso: {CertUtils.obter_common_name(cert_broker)}")
        chave_publica_broker = CertUtils.obter_chave_publica(cert_broker)

        chave_sessao = CryptoUtils.gerar_chave_simetrica()
        chave_sessao_cifrada = CryptoUtils.rsa_encrypt(chave_publica_broker, chave_sessao)
        self.canal.enviar({
            'acao': 'KEY_EXCHANGE',
            'chave_sessao': base64.b64encode(chave_sessao_cifrada).decode()
        })

        ack = self.canal.receber_um()
        if ack.get('acao') != 'SESSION_ESTABLISHED':
            raise ConnectionError("Falha ao estabelecer canal seguro com o broker.")

        self.canal.definir_chave_sessao(chave_sessao)
        print("🔒 Canal criptografado (envelopamento digital) estabelecido com o broker.")

    def _autenticar(self, client_id):
        """Envia o certificado do cliente e responde ao desafio de posse de chave privada."""
        self.canal.enviar({'acao': 'CLIENT_CERT', 'certificado': self.cert_cliente_pem})

        desafio = self.canal.receber_um()
        if desafio.get('acao') != 'AUTH_CHALLENGE':
            motivo = desafio.get('motivo', 'motivo desconhecido')
            raise ConnectionError(f"🚫 Autenticação de cliente recusada pelo broker: {motivo}")

        nonce = base64.b64decode(desafio['nonce'])
        assinatura = CryptoUtils.assinar_dados(self.chave_privada, nonce)
        self.canal.enviar({
            'acao': 'AUTH_RESPONSE',
            'assinatura': base64.b64encode(assinatura).decode(),
            'client_id': client_id
        })

        resultado = self.canal.receber_um()
        if resultado.get('acao') != 'AUTH_OK':
            motivo = resultado.get('motivo', 'motivo desconhecido')
            raise ConnectionError(f"🚫 Falha na autenticação do cliente: {motivo}")

        print(f"🔒 Autenticado no broker como '{client_id}'.")

    # ==========================================================================
    # OPERAÇÕES PUB/SUB
    # ==========================================================================

    def inscrever(self, topico):
        self.topicos_inscritos.add(topico)
        self.canal.enviar({'acao': 'SUBSCRIBE', 'topico': topico})

    def desinscrever(self, topico):
        if topico in self.topicos_inscritos:
            self.topicos_inscritos.remove(topico)
        self.canal.enviar({'acao': 'UNSUBSCRIBE', 'topico': topico})

    def publicar(self, topico, mensagem_clara):
        """Criptografa o payload individualmente para cada par conhecido do tópico
        (criptografia ponta-a-ponta: o broker roteia sem conseguir decifrar)."""
        peers = self.peers_por_topico.get(topico, {})

        if not peers:
            print(f"⚠️  Nenhum outro membro conhecido em '{topico}' ainda. "
                  f"A mensagem pode não chegar a ninguém (ninguém está inscrito, ou os "
                  f"certificados dos pares ainda não foram recebidos).")

        e2e = {}
        for cid, cert_peer in peers.items():
            chave_publica_peer = CertUtils.obter_chave_publica(cert_peer)
            chave_cifrada_b64, dados_cifrados_b64 = CryptoUtils.envelope_encrypt(
                chave_publica_peer, mensagem_clara.encode()
            )
            e2e[cid] = {'chave': chave_cifrada_b64, 'dados': dados_cifrados_b64}

        self.canal.enviar({'acao': 'PUBLISH', 'topico': topico, 'e2e': e2e})

    # ==========================================================================
    # ESCUTA DE MENSAGENS
    # ==========================================================================

    def escutar(self, callback=None):
        while True:
            try:
                dados = self.socket.recv(4096)
                if not dados:
                    print("Conexão com o Broker foi encerrada.")
                    break

                for pacote in self.canal.receber_disponiveis(dados):
                    self._tratar_pacote(pacote, callback)

            except Exception as e:
                print(f"Erro na escuta: {e}")
                break

    def _tratar_pacote(self, pacote, callback):
        acao = pacote.get('acao')

        if acao == 'CONNECT_ACK':
            topicos_recuperados = pacote.get('topicos_restaurados', [])
            for topico in topicos_recuperados:
                self.topicos_inscritos.add(topico)
            if callback:
                callback("SISTEMA",
                          f"Sessão restaurada! Suas inscrições ativas foram recuperadas: "
                          f"{', '.join(topicos_recuperados)}", "BROKER")

        elif acao == 'TOPIC_PEERS':
            topico = pacote['topico']
            self.peers_por_topico.setdefault(topico, {})
            for cid, cert_pem in pacote.get('peers', {}).items():
                try:
                    self.peers_por_topico[topico][cid] = CertUtils.pem_para_cert(cert_pem)
                except Exception:
                    continue

        elif acao == 'PEER_JOINED':
            topico = pacote['topico']
            cid = pacote['client_id']
            cert_pem = pacote.get('certificado')
            if cert_pem and cid != self.client_id:
                self.peers_por_topico.setdefault(topico, {})
                try:
                    self.peers_por_topico[topico][cid] = CertUtils.pem_para_cert(cert_pem)
                except Exception:
                    pass
                if callback:
                    callback("SISTEMA", f"'{cid}' entrou no tópico '{topico}'.", "BROKER")

        elif acao == 'RECEIVE':
            topico = pacote['topico']
            remetente = pacote.get('remetente', 'Desconhecido')
            bloco = pacote.get('e2e_para_mim')
            try:
                mensagem = CryptoUtils.envelope_decrypt(
                    self.chave_privada, bloco['chave'], bloco['dados']
                ).decode()
            except Exception as e:
                mensagem = f"[⚠️ Falha ao decifrar a mensagem ponta-a-ponta: {e}]"

            if callback:
                callback(topico, mensagem, remetente)
            else:
                print(f"\n[{remetente} em '{topico}']: {mensagem}")

        elif acao in ('AUTH_FAIL',):
            if callback:
                callback("SISTEMA", f"Autenticação falhou: {pacote.get('motivo')}", "BROKER")