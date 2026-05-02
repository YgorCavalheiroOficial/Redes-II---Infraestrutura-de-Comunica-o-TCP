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
        except Exception:
            return False