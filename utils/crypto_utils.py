import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet

class CryptoUtils:
    @staticmethod
    def gerar_par_chaves():
        """Gera um par de chaves RSA assimétrica (Pública e Privada)."""
        chave_privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        chave_publica = chave_privada.public_key()
        return chave_privada, chave_publica

    @staticmethod
    def gerar_chave_simetrica():
        """Gera uma chave simétrica para o envelopamento digital."""
        return Fernet.generate_key()

    @staticmethod
    def assinar_dados(chave_privada, dados):
        """Assina digitalmente os dados."""
        assinatura = chave_privada.sign(
            dados,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        return assinatura

    @staticmethod
    def verificar_assinatura(chave_publica, assinatura, dados):
        """Verifica a assinatura digital."""
        try:
            chave_publica.verify(
                assinatura,
                dados,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            print(f"[DEBUG] Erro REAL na verificação de assinatura: {type(e).__name__}: {e}")
            print(f"[DEBUG] Tipo da chave pública recebida: {type(chave_publica)}")
            print(f"[DEBUG] Tamanho da assinatura recebida (bytes): {len(assinatura)}")
            print(f"[DEBUG] Tamanho dos dados (nonce) (bytes): {len(dados)}")
            return False

    # =================================================================
    # ENVELOPAMENTO DIGITAL (criptografia híbrida RSA + simétrica)
    # Implementação própria, sem uso de TLS/SSL, conforme exigido na AV3.
    # =================================================================

    @staticmethod
    def rsa_encrypt(chave_publica, dados: bytes) -> bytes:
        """Criptografa dados PEQUENOS diretamente com RSA-OAEP (usado apenas
        para cifrar a chave de sessão simétrica, nunca o payload inteiro,
        já que RSA não é indicado para grandes volumes de dados)."""
        return chave_publica.encrypt(
            dados,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    @staticmethod
    def rsa_decrypt(chave_privada, dados: bytes) -> bytes:
        """Descriptografa dados cifrados com rsa_encrypt."""
        return chave_privada.decrypt(
            dados,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    @staticmethod
    def envelope_encrypt(chave_publica_destino, dados: bytes):
        """
        Envelopamento digital:
          1) Gera uma chave simétrica efêmera (Fernet = AES-128-CBC + HMAC-SHA256).
          2) Criptografa os DADOS com essa chave simétrica (rápido, qualquer tamanho).
          3) Criptografa a CHAVE SIMÉTRICA com a chave pública RSA do destinatário.
        Somente quem possuir a chave privada correspondente consegue abrir o envelope.
        Retorna uma tupla (chave_cifrada_b64, dados_cifrados_b64) pronta para ir em JSON.
        """
        chave_sessao = Fernet.generate_key()
        dados_cifrados = Fernet(chave_sessao).encrypt(dados)
        chave_cifrada = CryptoUtils.rsa_encrypt(chave_publica_destino, chave_sessao)
        return (
            base64.b64encode(chave_cifrada).decode(),
            base64.b64encode(dados_cifrados).decode()
        )

    @staticmethod
    def envelope_decrypt(chave_privada, chave_cifrada_b64: str, dados_cifrados_b64: str) -> bytes:
        """Abre um envelope digital criado por envelope_encrypt, usando a chave privada."""
        chave_cifrada = base64.b64decode(chave_cifrada_b64)
        dados_cifrados = base64.b64decode(dados_cifrados_b64)
        chave_sessao = CryptoUtils.rsa_decrypt(chave_privada, chave_cifrada)
        return Fernet(chave_sessao).decrypt(dados_cifrados)

    # ---- Cifragem simétrica usando uma chave de sessão já estabelecida ----
    # (usada para TODO o tráfego após o handshake inicial de envelopamento)

    @staticmethod
    def cifrar_com_chave_sessao(chave_sessao: bytes, dados: bytes) -> str:
        return Fernet(chave_sessao).encrypt(dados).decode()

    @staticmethod
    def decifrar_com_chave_sessao(chave_sessao: bytes, token: str) -> bytes:
        return Fernet(chave_sessao).decrypt(token.encode())