# ferramentas_teste/gerar_ambiente_teste.py
"""
FERRAMENTA SOMENTE PARA TESTES LOCAIS.
=======================================
Cria uma Autoridade Certificadora FALSA (auto-assinada) na sua máquina e usa
ela para assinar um certificado de teste para o broker e outro para o
cliente. Isso permite rodar e testar TODO o fluxo de handshake/autenticação/
criptografia ANTES de receber os certificados reais assinados pelo professor.

Gera tudo dentro de 'certificados_ac_teste/'. NÃO USE ESTES ARQUIVOS NA
ENTREGA FINAL DO TRABALHO - eles servem apenas para você validar que a
implementação funciona de ponta a ponta.

Uso:
    python ferramentas_teste/gerar_ambiente_teste.py

Depois, para testar localmente, aponte o Broker/Cliente para essa pasta, ex:

    Broker(caminho_cert_broker='certificados_ac_teste/broker_cert.crt',
           caminho_chave_broker='certificados_ac_teste/chave_privada_broker.pem',
           caminho_cert_ca='certificados_ac_teste/certificado_ac.crt')

    Cliente(caminho_cert_cliente='certificados_ac_teste/certificado_cliente.crt',
            caminho_chave_cliente='certificados_ac_teste/chave_privada_cliente.pem',
            caminho_cert_ca='certificados_ac_teste/certificado_ac.crt')
"""
import datetime
import os

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

SAIDA = os.path.join(os.path.dirname(__file__), "..", "certificados_ac_teste")
SAIDA = os.path.abspath(SAIDA)


def _salvar_chave(chave, caminho):
    with open(caminho, "wb") as f:
        f.write(chave.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))


def _salvar_cert(cert, caminho):
    with open(caminho, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def _gerar_ca():
    chave_ca = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome_ca = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "IFSC - AC de TESTE (nao usar na entrega)"),
        x509.NameAttribute(NameOID.COMMON_NAME, "AC-Teste-Local"),
    ])
    agora = datetime.datetime.now(datetime.timezone.utc)
    cert_ca = (
        x509.CertificateBuilder()
        .subject_name(nome_ca)
        .issuer_name(nome_ca)
        .public_key(chave_ca.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora)
        .not_valid_after(agora + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(chave_ca, hashes.SHA256())
    )
    return chave_ca, cert_ca


def _emitir_certificado(cn, chave_ca, cert_ca):
    chave_entidade = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome_entidade = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "SC"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Lages"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "IFSC"),
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
    ])
    agora = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(nome_entidade)
        .issuer_name(cert_ca.subject)
        .public_key(chave_entidade.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora)
        .not_valid_after(agora + datetime.timedelta(days=365))
        .sign(chave_ca, hashes.SHA256())
    )
    return chave_entidade, cert


def main():
    os.makedirs(SAIDA, exist_ok=True)

    print("Gerando AC de teste (auto-assinada)...")
    chave_ca, cert_ca = _gerar_ca()
    _salvar_chave(chave_ca, os.path.join(SAIDA, "chave_privada_ac_teste.pem"))
    _salvar_cert(cert_ca, os.path.join(SAIDA, "certificado_ac.crt"))

    print("Emitindo certificado de teste para o BROKER...")
    chave_broker, cert_broker = _emitir_certificado("Broker_AV3_TESTE", chave_ca, cert_ca)
    _salvar_chave(chave_broker, os.path.join(SAIDA, "chave_privada_broker.pem"))
    _salvar_cert(cert_broker, os.path.join(SAIDA, "broker_cert.crt"))

    print("Emitindo certificado de teste para o CLIENTE...")
    chave_cliente, cert_cliente = _emitir_certificado("Cliente_Teste_AV3", chave_ca, cert_ca)
    _salvar_chave(chave_cliente, os.path.join(SAIDA, "chave_privada_cliente.pem"))
    _salvar_cert(cert_cliente, os.path.join(SAIDA, "certificado_cliente.crt"))

    print(f"\n✅ Ambiente de teste completo gerado em: {SAIDA}")
    print("⚠️  Estes certificados são FALSOS e servem só para testar localmente.")
    print("⚠️  Para a entrega final, use o certificado REAL assinado pelo professor.")


if __name__ == "__main__":
    main()
