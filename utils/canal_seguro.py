"""
canal_seguro.py
----------------
Encapsula um socket TCP cru, cuidando de:
  1) Enquadramento das mensagens JSON (delimitadas por '\n');
  2) Criptografia SIMÉTRICA de sessão (chave estabelecida no envelopamento digital),
     aplicada a TODO o tráfego trocado depois do handshake inicial.

Antes da chave de sessão ser definida (durante a fase inicial de troca de
certificados/chave), os pacotes trafegam em texto puro (o próprio certificado
não é sigiloso, e o pacote KEY_EXCHANGE já vem com a chave simétrica protegida
por RSA). A partir do momento em que `definir_chave_sessao` é chamado, todo
pacote enviado/recebido passa a ser cifrado (Fernet) automaticamente.
"""

import json
from utils.crypto_utils import CryptoUtils


class CanalSeguro:

    def __init__(self, sock):
        self.sock = sock
        self.buffer = ""
        self.chave_sessao = None  # bytes | None -> definida após o handshake

    def definir_chave_sessao(self, chave: bytes):
        self.chave_sessao = chave

    # ---------------------------- Envio ----------------------------

    def enviar(self, dicionario: dict):
        texto = json.dumps(dicionario)
        if self.chave_sessao:
            linha = CryptoUtils.cifrar_com_chave_sessao(self.chave_sessao, texto.encode())
        else:
            linha = texto
        self.sock.send((linha + "\n").encode())

    # ---------------------------- Recebimento ----------------------------

    def _decodificar_linha(self, linha: str) -> dict:
        if self.chave_sessao:
            dados = CryptoUtils.decifrar_com_chave_sessao(self.chave_sessao, linha)
            return json.loads(dados.decode())
        return json.loads(linha)

    def receber_um(self, tamanho_bloco: int = 4096) -> dict:
        """Bloqueia a thread atual até obter e decodificar EXATAMENTE um pacote.
        Usado apenas durante o handshake síncrono (troca de certificados/chaves)."""
        while "\n" not in self.buffer:
            dados = self.sock.recv(tamanho_bloco)
            if not dados:
                raise ConnectionError("Conexão encerrada pelo par remoto durante o handshake.")
            self.buffer += dados.decode()
        linha, self.buffer = self.buffer.split("\n", 1)
        linha = linha.strip()
        return self._decodificar_linha(linha)

    def receber_disponiveis(self, dados_brutos: bytes) -> list:
        """Alimenta o buffer interno com bytes recebidos via socket.recv() e
        devolve a lista de pacotes JSON já decodificados/decifrados que
        estiverem completos. Usado no loop de eventos assíncrono principal."""
        self.buffer += dados_brutos.decode()
        pacotes = []
        while "\n" in self.buffer:
            linha, self.buffer = self.buffer.split("\n", 1)
            linha = linha.strip()
            if linha:
                pacotes.append(self._decodificar_linha(linha))
        return pacotes
