# certificados_ac/gerar_requisicao_broker.py
"""
Gera o par de chaves RSA do BROKER e o CSR (Certificate Signing Request) que
deve ser enviado ao professor para assinatura.

Rode este script UMA VEZ (na máquina que vai rodar o broker) e envie o
arquivo 'broker.csr' resultante ao professor. Quando ele devolver o .crt
assinado, salve-o em 'certificados_ac/broker_cert.crt'.

NÃO envie 'chave_privada_broker.pem' a ninguém - ela deve permanecer secreta.
"""
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os


def gerar_solicitacao_certificado_broker():
    print("Gerando par de chaves RSA para o BROKER...")
    chave_privada = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    caminho_privada = os.path.join(os.path.dirname(__file__), "chave_privada_broker.pem")
    with open(caminho_privada, "wb") as f:
        f.write(chave_privada.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print(f"✅ Chave privada do broker salva em: {caminho_privada}")

    print("Criando o arquivo de requisição (CSR) do broker...")
    identidade = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "SC"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Lages"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "IFSC"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Broker_AV3"),  # Altere se o professor pedir outro CN
    ])

    csr = x509.CertificateSigningRequestBuilder().subject_name(
        identidade
    ).sign(chave_privada, hashes.SHA256())

    caminho_csr = os.path.join(os.path.dirname(__file__), "broker.csr")
    with open(caminho_csr, "wb") as f:
        f.write(csr.public_bytes(serialization.Encoding.PEM))

    print(f"✅ CONCLUÍDO! Envie o arquivo '{caminho_csr}' para o professor assinar.")
    print("   Quando receber de volta, salve o .crt assinado como 'broker_cert.crt' nesta pasta.")


if __name__ == "__main__":
    gerar_solicitacao_certificado_broker()
