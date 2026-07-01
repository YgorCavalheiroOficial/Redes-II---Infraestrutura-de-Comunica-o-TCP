# certificado/gerar_requisicao.py
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os

def gerar_solicitacao_certificado():
    print("Gerando par de chaves RSA para o cliente...")
    # 1. Gera a chave privada do cliente
    chave_privada = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # 2. Salva a chave privada localmente (NUNCA envie este arquivo a ninguém)
    caminho_privada = os.path.join(os.path.dirname(__file__), "chave_privada_cliente.pem")
    with open(caminho_privada, "wb") as f:
        f.write(chave_privada.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"✅ Chave privada salva em: {caminho_privada}")

    # 3. Cria a Requisição de Assinatura de Certificado (CSR)
    print("Criando o arquivo de requisição (CSR)...")
    identidade = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "SC"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Lages"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "IFSC"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Cliente_Identificador_AV3"), # Altere com seu nome se quiser
    ])

    csr = x509.CertificateSigningRequestBuilder().subject_name(
        identidade
    ).sign(chave_privada, hashes.SHA256())

    # 4. Salva o arquivo .csr que será enviado ao professor
    caminho_csr = os.path.join(os.path.dirname(__file__), "cliente.csr")
    with open(caminho_csr, "wb") as f:
        f.write(csr.public_bytes(serialization.Encoding.PEM))
    
    print(f"✅ CONCLUÍDO! Pegue o arquivo '{caminho_csr}' e envie para o seu professor assinar.")

if __name__ == "__main__":
    gerar_solicitacao_certificado()