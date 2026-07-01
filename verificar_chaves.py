"""
verificar_chaves.py
--------------------
Script de diagnóstico: confere se cada certificado (.crt) realmente
corresponde à chave privada (.pem) que deveria acompanhá-lo.

Rode este arquivo de dentro da pasta raiz do projeto
(Redes-II---Infraestrutura-de-Comunica-o-TCP), ou ajuste o caminho
CERT_DIR abaixo se necessário.

Uso:
    python verificar_chaves.py
"""

import os
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

CERT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "certificados_ac")


def carregar_cert(caminho):
    with open(caminho, "rb") as f:
        return x509.load_pem_x509_certificate(f.read())


def carregar_chave_privada(caminho):
    with open(caminho, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def modulus_da_chave_publica(chave_publica):
    numeros = chave_publica.public_numbers()
    return numeros.n


def conferir_par(nome, caminho_cert, caminho_chave):
    print(f"\n--- {nome} ---")
    if not os.path.exists(caminho_cert):
        print(f"❌ Certificado não encontrado: {caminho_cert}")
        return
    if not os.path.exists(caminho_chave):
        print(f"❌ Chave privada não encontrada: {caminho_chave}")
        return

    try:
        cert = carregar_cert(caminho_cert)
    except Exception as e:
        print(f"❌ Erro ao carregar o certificado ({caminho_cert}): {e}")
        return

    try:
        chave_privada = carregar_chave_privada(caminho_chave)
    except Exception as e:
        print(f"❌ Erro ao carregar a chave privada ({caminho_chave}): {e}")
        return

    modulus_cert = modulus_da_chave_publica(cert.public_key())
    modulus_chave = modulus_da_chave_publica(chave_privada.public_key())

    if modulus_cert == modulus_chave:
        print(f"✅ CASAM! A chave privada corresponde à chave pública do certificado.")
    else:
        print(f"❌ NÃO CASAM! Essa chave privada NÃO gera a chave pública deste certificado.")
        print(f"   (Módulo do cert:  {hex(modulus_cert)[:40]}...)")
        print(f"   (Módulo da chave: {hex(modulus_chave)[:40]}...)")


def comparar_arquivos_brutos(nome, caminho_a, caminho_b):
    print(f"\n--- Comparação byte-a-byte: {nome} ---")
    try:
        with open(caminho_a, "rb") as fa, open(caminho_b, "rb") as fb:
            conteudo_a = fa.read()
            conteudo_b = fb.read()
        if conteudo_a == conteudo_b:
            print("✅ Os dois arquivos são IDÊNTICOS byte a byte.")
        else:
            print("⚠️  Os arquivos são DIFERENTES (mesmo que o conteúdo pareça igual visualmente).")
            print(f"   Tamanho A: {len(conteudo_a)} bytes | Tamanho B: {len(conteudo_b)} bytes")
    except FileNotFoundError as e:
        print(f"❌ {e}")


if __name__ == "__main__":
    print(f"Verificando certificados em: {CERT_DIR}\n")
    print("=" * 60)

    conferir_par(
        "CLIENTE (certificado_cliente.crt <-> chave_privada_cliente.pem)",
        os.path.join(CERT_DIR, "certificado_cliente.crt"),
        os.path.join(CERT_DIR, "chave_privada_cliente.pem"),
    )

    conferir_par(
        "BROKER (broker_cert.crt <-> chave_privada_broker.pem)",
        os.path.join(CERT_DIR, "broker_cert.crt"),
        os.path.join(CERT_DIR, "chave_privada_broker.pem"),
    )

    comparar_arquivos_brutos(
        "certificado_cliente.crt vs broker_cert.crt",
        os.path.join(CERT_DIR, "certificado_cliente.crt"),
        os.path.join(CERT_DIR, "broker_cert.crt"),
    )

    comparar_arquivos_brutos(
        "chave_privada_cliente.pem vs chave_privada_broker.pem",
        os.path.join(CERT_DIR, "chave_privada_cliente.pem"),
        os.path.join(CERT_DIR, "chave_privada_broker.pem"),
    )

    print("\n" + "=" * 60)
    print("Diagnóstico concluído.")