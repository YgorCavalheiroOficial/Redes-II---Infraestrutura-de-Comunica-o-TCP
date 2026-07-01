"""
cert_utils.py
--------------
Utilitários para carregar, serializar e VERIFICAR certificados digitais X.509.

Requisito da AV3: tanto o cliente quanto o broker precisam validar a assinatura
de um certificado (do broker ou do cliente, respectivamente) contra o
certificado público da Autoridade Certificadora (AC) - o professor da disciplina.
"""

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature


class CertUtils:

    # ---------------------- Carregamento a partir de arquivo ----------------------

    @staticmethod
    def carregar_certificado(caminho: str) -> x509.Certificate:
        """Lê um arquivo .crt/.pem (PEM) do disco e devolve o objeto Certificate."""
        with open(caminho, "rb") as f:
            return x509.load_pem_x509_certificate(f.read())

    @staticmethod
    def carregar_chave_privada(caminho: str):
        """Lê uma chave privada RSA (PEM, sem senha) do disco."""
        with open(caminho, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    # ---------------------- Conversão PEM <-> objeto (para trafegar na rede) -------

    @staticmethod
    def cert_para_pem(cert: x509.Certificate) -> str:
        """Serializa um certificado para string PEM (para enviar pela rede em JSON)."""
        return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")

    @staticmethod
    def pem_para_cert(pem_str: str) -> x509.Certificate:
        """Reconstrói um objeto Certificate a partir de uma string PEM recebida pela rede."""
        return x509.load_pem_x509_certificate(pem_str.encode("utf-8"))

    # ---------------------- Verificação de confiança (núcleo de segurança) ---------

    @staticmethod
    def verificar_certificado(cert: x509.Certificate, cert_ca: x509.Certificate) -> bool:
        """
        Verifica se 'cert' foi realmente assinado pela chave privada correspondente
        à chave pública contida em 'cert_ca' (ou seja, confirma que a AC assinou o certificado).

        Isso é equivalente ao que acontece ao validar uma cadeia de confiança:
        pegamos a assinatura contida no certificado e conferimos usando a chave
        pública do emissor (a AC).
        """
        chave_publica_ca = cert_ca.public_key()
        try:
            chave_publica_ca.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm,
            )
            return True
        except InvalidSignature:
            return False
        except Exception:
            # Qualquer outro erro (algoritmo incompatível, certificado corrompido, etc.)
            # também deve ser tratado como "não confiável".
            return False

    @staticmethod
    def certificado_valido_no_periodo(cert: x509.Certificate) -> bool:
        """Confere se o certificado está dentro do prazo de validade (not_before / not_after)."""
        import datetime
        agora = datetime.datetime.now(datetime.timezone.utc)
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc
        return not_before <= agora <= not_after

    @staticmethod
    def obter_chave_publica(cert: x509.Certificate):
        """Extrai a chave pública RSA embutida no certificado."""
        return cert.public_key()

    @staticmethod
    def obter_common_name(cert: x509.Certificate) -> str:
        """Extrai o Common Name (CN) do subject do certificado, útil para logs/identificação."""
        try:
            return cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
        except (IndexError, Exception):
            return "desconhecido"
