import sys, os, time, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from broker.servidor import Broker
from cliente.aplicacao_cliente import Cliente

TESTE_DIR = os.path.join(os.path.dirname(__file__), "..", "certificados_ac_teste")

def start_broker():
    broker = Broker(
        host='127.0.0.1', port=18844,
        caminho_cert_broker=os.path.join(TESTE_DIR, "broker_cert.crt"),
        caminho_chave_broker=os.path.join(TESTE_DIR, "chave_privada_broker.pem"),
        caminho_cert_ca=os.path.join(TESTE_DIR, "certificado_ac.crt"),
    )
    t = threading.Thread(target=broker.start, daemon=True)
    t.start()
    return broker

def make_client():
    return Cliente(
        broker_host='127.0.0.1', broker_port=18844,
        caminho_cert_cliente=os.path.join(TESTE_DIR, "certificado_cliente.crt"),
        caminho_chave_cliente=os.path.join(TESTE_DIR, "chave_privada_cliente.pem"),
        caminho_cert_ca=os.path.join(TESTE_DIR, "certificado_ac.crt"),
    )

recebidas = []

def cb_factory(nome):
    def cb(topico, msg, remetente):
        print(f"[{nome} recebeu] topico={topico} remetente={remetente} msg={msg!r}")
        recebidas.append((nome, topico, msg, remetente))
    return cb

if __name__ == "__main__":
    print("== Subindo broker de teste ==")
    start_broker()
    time.sleep(0.5)

    print("== Conectando cliente A ==")
    a = make_client()
    a.conectar("cliente_A")
    ta = threading.Thread(target=a.escutar, args=(cb_factory("A"),), daemon=True)
    ta.start()

    print("== Conectando cliente B ==")
    b = make_client()
    b.conectar("cliente_B")
    tb = threading.Thread(target=b.escutar, args=(cb_factory("B"),), daemon=True)
    tb.start()

    time.sleep(0.3)
    print("== Ambos inscrevem no topico 'geral' ==")
    a.inscrever("geral")
    time.sleep(0.3)
    b.inscrever("geral")
    time.sleep(0.5)

    print("== A publica mensagem ==")
    a.publicar("geral", "Ola B, isso e um teste E2E cifrado!")
    time.sleep(1.0)

    mensagens_reais = [r for r in recebidas if r[1] == "geral"]
    assert len(mensagens_reais) == 1, f"Esperava 1 mensagem no topico 'geral', obteve {mensagens_reais}"
    nome, topico, msg, remetente = mensagens_reais[0]
    assert nome == "B" and remetente == "cliente_A" and "teste E2E" in msg
    print("\n✅✅✅ TESTE DE INTEGRACAO PASSOU: handshake, autenticacao mutua e E2E funcionando. ✅✅✅")
