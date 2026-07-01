import sys, os, time, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from broker.servidor import Broker
from cliente.aplicacao_cliente import Cliente

TESTE_DIR = os.path.join(os.path.dirname(__file__), "..", "certificados_ac_teste")

# Gera uma segunda AC "impostora" + certificado de cliente assinado por ela,
# para simular um atacante tentando se passar por cliente legitimo.
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

IMPOSTOR_DIR = os.path.join(os.path.dirname(__file__), "..", "certificados_ac_impostor_teste")
os.makedirs(IMPOSTOR_DIR, exist_ok=True)

def _salvar_chave(chave, caminho):
    with open(caminho, "wb") as f:
        f.write(chave.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))

def _salvar_cert(cert, caminho):
    with open(caminho, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

chave_ca_fake = rsa.generate_private_key(public_exponent=65537, key_size=2048)
nome_ca_fake = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AC-IMPOSTORA")])
agora = datetime.datetime.now(datetime.timezone.utc)
cert_ca_fake = x509.CertificateBuilder().subject_name(nome_ca_fake).issuer_name(nome_ca_fake)\
    .public_key(chave_ca_fake.public_key()).serial_number(x509.random_serial_number())\
    .not_valid_before(agora).not_valid_after(agora+datetime.timedelta(days=365))\
    .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)\
    .sign(chave_ca_fake, hashes.SHA256())

chave_cliente_fake = rsa.generate_private_key(public_exponent=65537, key_size=2048)
nome_cliente_fake = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "cliente_MALICIOSO")])
cert_cliente_fake = x509.CertificateBuilder().subject_name(nome_cliente_fake).issuer_name(cert_ca_fake.subject)\
    .public_key(chave_cliente_fake.public_key()).serial_number(x509.random_serial_number())\
    .not_valid_before(agora).not_valid_after(agora+datetime.timedelta(days=365))\
    .sign(chave_ca_fake, hashes.SHA256())

_salvar_chave(chave_cliente_fake, os.path.join(IMPOSTOR_DIR, "chave_privada_cliente.pem"))
_salvar_cert(cert_cliente_fake, os.path.join(IMPOSTOR_DIR, "certificado_cliente.crt"))

def start_broker():
    broker = Broker(
        host='127.0.0.1', port=18855,
        caminho_cert_broker=os.path.join(TESTE_DIR, "broker_cert.crt"),
        caminho_chave_broker=os.path.join(TESTE_DIR, "chave_privada_broker.pem"),
        caminho_cert_ca=os.path.join(TESTE_DIR, "certificado_ac.crt"),
    )
    threading.Thread(target=broker.start, daemon=True).start()

if __name__ == "__main__":
    print("== Subindo broker de teste (confia apenas na AC-Teste-Local) ==")
    start_broker()
    time.sleep(0.5)

    print("== Tentando conectar com certificado assinado por AC IMPOSTORA (deve ser rejeitado) ==")
    intruso = Cliente(
        broker_host='127.0.0.1', broker_port=18855,
        caminho_cert_cliente=os.path.join(IMPOSTOR_DIR, "certificado_cliente.crt"),
        caminho_chave_cliente=os.path.join(IMPOSTOR_DIR, "chave_privada_cliente.pem"),
        caminho_cert_ca=os.path.join(TESTE_DIR, "certificado_ac.crt"),  # intruso confia na AC certa (nao importa p/ este teste)
    )
    try:
        intruso.conectar("cliente_MALICIOSO")
        print("❌ FALHA DE SEGURANCA: o broker aceitou um certificado nao confiavel!")
        sys.exit(1)
    except ConnectionError as e:
        print(f"✅ Broker rejeitou corretamente: {e}")

    print("\n✅✅✅ TESTE NEGATIVO PASSOU. ✅✅✅")
