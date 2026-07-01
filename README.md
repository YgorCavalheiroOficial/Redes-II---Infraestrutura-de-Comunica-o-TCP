# Redes II - Infraestrutura de Comunicação TCP

Projeto acadêmico da disciplina de **Redes de Computadores II (IFSC - Câmpus Lages)**.

Implementa uma infraestrutura de comunicação `publish/subscribe` (semelhante ao
MQTT) sobre **TCP**, com:

- **Envelopamento digital próprio** (sem uso de TLS/SSL) para proteger todo o
  tráfego entre cliente e broker contra terceiros (ex.: man-in-the-middle).
- **Autenticação mútua por certificado digital** (Broker ⇄ Cliente), validada
  contra uma Autoridade Certificadora (AC) — o professor da disciplina.
- **Criptografia ponta-a-ponta** entre clientes: o broker roteia as mensagens
  sem nunca conseguir decifrar o conteúdo do payload.

---

## ⚠️ Antes de rodar: você precisa de 2 arquivos que só o professor fornece

O repositório **não** inclui segredos/certificados reais (ficam de fora do
git, veja `.gitignore`). Para rodar com dados reais, você precisa colocar em
`certificados_ac/`:

| Arquivo | O que é | Como obter |
|---|---|---|
| `certificado_ac.crt` | Certificado público **da própria AC** (autoassinado, `Issuer == Subject`) | Pedir ao professor (é diferente do certificado assinado que ele te devolveu como cliente) |
| `broker_cert.crt` + `chave_privada_broker.pem` | Identidade do broker, assinada pela AC | Rodar `certificados_ac/gerar_requisicao_broker.py`, enviar o `.csr` gerado ao professor e salvar o `.crt` que ele devolver |
| `certificado_assinado_pela_AC_<nome>.crt` + `chave_privada_cliente.pem` | Identidade do cliente, assinada pela AC | Rodar `certificados_ac/gerar_requisicao.py` e enviar o `.csr` ao professor |

Detalhes completos e um passo-a-passo de teste local (sem depender do
professor) estão em **[`SETUP.md`](./SETUP.md)**.

---

## Como rodar

```bash
pip install -r requirements.txt

# Terminal 1
python main_broker.py

# Terminal 2 (interface gráfica)
python main_gui.py

# ...ou modo texto
python main_cliente.py
```

Cada cliente pede um `client_id` único ao conectar. Depois de autenticado,
use os botões/menus para se inscrever em tópicos, publicar e receber
mensagens — tudo cifrado de ponta a ponta entre os clientes.

## Testando sem certificados reais

```bash
python ferramentas_teste/gerar_ambiente_teste.py   # cria uma AC de teste local
python ferramentas_teste/teste_integracao.py       # handshake + auth mútua + E2E
python ferramentas_teste/teste_rejeicao.py         # confirma rejeição de certificado inválido
```

---

## Estrutura do projeto

```
main_broker.py              # ponto de entrada do broker
main_cliente.py             # cliente em modo texto
main_gui.py                 # cliente com interface gráfica (Tkinter)

broker/
  servidor.py                # Broker: handshake, autenticação mútua, roteamento pub/sub

cliente/
  aplicacao_cliente.py        # Cliente: handshake, autenticação, publish/subscribe, e2e

utils/
  cert_utils.py                # Carregar/serializar/verificar certificados X.509
  crypto_utils.py              # RSA, assinatura digital e envelopamento digital híbrido
  canal_seguro.py              # Enquadramento das mensagens + cifragem simétrica de sessão

certificados_ac/
  gerar_requisicao.py           # Gera CSR + chave do CLIENTE
  gerar_requisicao_broker.py    # Gera CSR + chave do BROKER
  (certificado_ac.crt, broker_cert.crt, chave_privada_*.pem  -> não versionados)

ferramentas_teste/
  gerar_ambiente_teste.py       # Cria uma AC + certificados de teste (uso local apenas)
  teste_integracao.py           # Testa o fluxo completo: handshake, auth, e2e
  teste_rejeicao.py             # Testa rejeição de certificado não confiável
```

## Protocolo de segurança (resumo)

1. **Handshake TCP** — conexão normal.
2. **Envelopamento digital** — broker envia seu certificado; cliente o valida
   contra a AC, gera uma chave de sessão simétrica e a envia cifrada com a
   chave pública do broker (RSA-OAEP). Daí em diante, **todo** o tráfego nos
   dois sentidos é cifrado com essa chave de sessão.
3. **Autenticação do cliente** — cliente envia seu certificado; o broker o
   valida contra a AC e envia um desafio aleatório que o cliente deve assinar
   com sua chave privada, provando posse da chave (não só posse do arquivo
   `.crt`).
4. **Publish/Subscribe** — ao se inscrever num tópico, o cliente recebe os
   certificados públicos dos demais membros. Ao publicar, ele monta um
   envelope de criptografia individual (RSA + simétrica) para cada
   destinatário; o broker roteia esses blocos sem conseguir decifrá-los.

Mais detalhes de implementação, arquivo por arquivo, em [`SETUP.md`](./SETUP.md).

## Licença

Ver [`LICENSE`](./LICENSE).