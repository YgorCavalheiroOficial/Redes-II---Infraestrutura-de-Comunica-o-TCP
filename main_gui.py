import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog
import threading
from cliente.aplicacao_cliente import Cliente

class ClienteGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WhatsApp Pub/Sub - Dashboard")
        self.root.geometry("620x620")
        
        # Cor de fundo da janela principal (Fundo padrão do WhatsApp Dark Mode)
        self.root.configure(bg="#0b141a")
        
        # Inicializa o cliente padrão do seu projeto
        try:
            self.cliente = Cliente(broker_host='127.0.0.1', broker_port=1024)
        except Exception as e:
            messagebox.showerror("Erro de Certificado", f"Não foi possível carregar os certificados:\n{e}")
            self.root.destroy()
            return
        
        # Construção da Interface Moderna
        self.criar_widgets()
        
        # Conecta automaticamente ao iniciar
        self.conectar_ao_broker()

    def criar_widgets(self):
        # --- PALETA DE CORES WHATSAPP DARK MODE ---
        self.BG_MAIN = "#0b141a"        # Fundo geral ultra-escuro
        self.BG_PANEL = "#202c33"       # Fundo dos painéis e blocos (Cabeçalhos)
        self.BG_ENTRY = "#2a3942"       # Fundo das caixas de entrada de texto
        self.FG_PRIMARY = "#e9edef"     # Texto principal (Branco suave)
        self.FG_SECONDARY = "#8696a0"   # Texto secundário (Cinza mutado)
        self.WA_GREEN = "#00a884"       # Verde padrão do WhatsApp para confirmações
        self.WA_RED = "#ef4444"         # Vermelho moderno para saídas/erros
        self.WA_BLUE = "#53bdeb"        # Azul suave para tópicos e destaques

        # Fontes Modernas
        font_title = ("Segoe UI", 10, "bold")
        font_body = ("Segoe UI", 10)
        font_bold = ("Segoe UI", 10, "bold")

        # --- HEADER / STATUS ---
        self.frame_status = tk.Frame(self.root, bg=self.BG_PANEL, bd=0)
        self.frame_status.pack(fill="x", padx=15, pady=10)
        
        self.lbl_status = tk.Label(self.frame_status, text="● TENTANDO CONEXÃO...", fg="orange", bg=self.BG_PANEL, font=font_bold)
        self.lbl_status.pack(pady=12)

        # --- SEÇÃO DE INSCRIÇÃO (SUBSCRIBE / UNSUBSCRIBE) ---
        self.frame_sub = tk.Frame(self.root, bg=self.BG_PANEL, bd=0)
        self.frame_sub.pack(fill="x", padx=15, pady=5)
        
        # Título interno simulando um card moderno
        tk.Label(self.frame_sub, text="Gerenciar Inscrições", fg=self.WA_GREEN, bg=self.BG_PANEL, font=font_title).grid(row=0, column=0, columnspan=4, padx=12, pady=(10, 5), sticky="w")
        
        tk.Label(self.frame_sub, text="Tópico:", fg=self.FG_PRIMARY, bg=self.BG_PANEL, font=font_body).grid(row=1, column=0, padx=(12, 5), pady=10, sticky="w")
        self.entry_topico_sub = tk.Entry(self.frame_sub, width=22, bg=self.BG_ENTRY, fg=self.FG_PRIMARY, insertbackground=self.FG_PRIMARY, relief="flat", font=font_body)
        self.entry_topico_sub.grid(row=1, column=1, padx=5, pady=10)
        
        self.btn_sub = tk.Button(self.frame_sub, text="Inscrever", bg=self.WA_GREEN, fg=self.FG_PRIMARY, font=font_bold, relief="flat", padx=12, pady=3, command=self.acao_inscrever, cursor="hand2", activebackground="#008f70", activeforeground=self.FG_PRIMARY)
        self.btn_sub.grid(row=1, column=2, padx=5, pady=10)
        
        self.btn_unsub = tk.Button(self.frame_sub, text="Sair", bg=self.WA_RED, fg=self.FG_PRIMARY, font=font_bold, relief="flat", padx=12, pady=3, command=self.acao_desinscrever, cursor="hand2", activebackground="#b91c1c", activeforeground=self.FG_PRIMARY)
        self.btn_unsub.grid(row=1, column=3, padx=5, pady=10)
        
        self.lbl_meus_topicos = tk.Label(self.frame_sub, text="Inscrito em: nenhum", fg=self.FG_SECONDARY, bg=self.BG_PANEL, font=("Segoe UI", 9, "italic"))
        self.lbl_meus_topicos.grid(row=2, column=0, columnspan=4, padx=12, pady=(0, 10), sticky="w")

        # --- SEÇÃO DE PUBLICAÇÃO (PUBLISH) ---
        self.frame_pub = tk.Frame(self.root, bg=self.BG_PANEL, bd=0)
        self.frame_pub.pack(fill="x", padx=15, pady=5)
        
        tk.Label(self.frame_pub, text="Publicar Mensagem", fg=self.WA_BLUE, bg=self.BG_PANEL, font=font_title).grid(row=0, column=0, columnspan=4, padx=12, pady=(10, 5), sticky="w")
        
        tk.Label(self.frame_pub, text="Canal Alvo:", fg=self.FG_PRIMARY, bg=self.BG_PANEL, font=font_body).grid(row=1, column=0, padx=(12, 5), pady=5, sticky="w")
        self.entry_topico_pub = tk.Entry(self.frame_pub, width=22, bg=self.BG_ENTRY, fg=self.FG_PRIMARY, insertbackground=self.FG_PRIMARY, relief="flat", font=font_body)
        self.entry_topico_pub.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(self.frame_pub, text="Mensagem:", fg=self.FG_PRIMARY, bg=self.BG_PANEL, font=font_body).grid(row=2, column=0, padx=(12, 5), pady=8, sticky="w")
        self.entry_mensagem = tk.Entry(self.frame_pub, width=32, bg=self.BG_ENTRY, fg=self.FG_PRIMARY, insertbackground=self.FG_PRIMARY, relief="flat", font=font_body)
        self.entry_mensagem.grid(row=2, column=1, columnspan=2, padx=5, pady=8, sticky="w")
        
        self.btn_pub = tk.Button(self.frame_pub, text="Enviar", bg=self.WA_GREEN, fg=self.FG_PRIMARY, font=font_bold, relief="flat", padx=18, pady=3, command=self.acao_publicar, cursor="hand2", activebackground="#008f70", activeforeground=self.FG_PRIMARY)
        self.btn_pub.grid(row=2, column=3, padx=5, pady=8)

        # --- PAINEL DE MONITORAMENTO (FEED DE CONVERSAS) ---
        self.frame_monitor = tk.Frame(self.root, bg=self.BG_PANEL, bd=0)
        self.frame_monitor.pack(fill="both", expand=True, padx=15, pady=10)
        
        tk.Label(self.frame_monitor, text="Conversas Ativas", fg=self.FG_PRIMARY, bg=self.BG_PANEL, font=font_title).pack(anchor="w", padx=12, pady=(10, 5))
        
        # Caixa do chat configurada exatamente com o fundo de conversa escuro do WhatsApp
        self.txt_feed = scrolledtext.ScrolledText(self.frame_monitor, bg=self.BG_MAIN, fg=self.FG_PRIMARY, insertbackground=self.FG_PRIMARY, relief="flat", font=("Consolas", 10))
        self.txt_feed.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def conectar_ao_broker(self):
        client_id = tk.simpledialog.askstring("Identidade do Cliente", "Digite o seu nome/ID único:")
        
        if not client_id:
            messagebox.showerror("Erro", "Você precisa digitar um ID para usar o sistema.")
            self.root.destroy()
            return

        try:
            self.root.title(f"WhatsApp Pub/Sub - Logado como: {client_id}")
            self.cliente.conectar(client_id)
            self.lbl_status.config(text=f"● CONECTADO COMO {client_id.upper()}", fg=self.WA_GREEN)
            
            thread_escuta = threading.Thread(target=self.cliente.escutar, args=(self.atualizar_feed_mensagens,), daemon=True)
            thread_escuta.start()
        except Exception as e:
            self.lbl_status.config(text="● FALHA AO CONECTAR", fg=self.WA_RED)
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar:\n{e}")

    def atualizar_label_topicos(self):
        lista_topicos = list(self.cliente.topicos_inscritos)
        if lista_topicos:
            self.lbl_meus_topicos.config(text=f"Inscrito em: {', '.join(lista_topicos)}", fg=self.WA_BLUE)
        else:
            self.lbl_meus_topicos.config(text="Inscrito em: nenhum", fg=self.FG_SECONDARY)

    def acao_inscrever(self):
        topico = self.entry_topico_sub.get().strip()
        if not topico:
            messagebox.showwarning("Campo Vazio", "Digite um tópico para se inscrever.")
            return
        
        self.cliente.inscrever(topico)
        self.atualizar_label_topicos()
        self.txt_feed.insert(tk.END, f"⚙️ [SISTEMA]: Inscrição enviada para o tópico '{topico}'\n")
        self.txt_feed.see(tk.END)
        self.entry_topico_sub.delete(0, tk.END)

    def acao_desinscrever(self):
        topico = self.entry_topico_sub.get().strip()
        if not topico:
            messagebox.showwarning("Campo Vazio", "Digite o tópico que deseja cancelar no campo ao lado.")
            return
        
        if topico not in self.cliente.topicos_inscritos:
            messagebox.showwarning("Aviso", f"Você não está inscrito no tópico '{topico}'.")
            return
            
        self.cliente.desinscrever(topico)
        self.atualizar_label_topicos()
        self.txt_feed.insert(tk.END, f"⚙️ [SISTEMA]: Cancelamento do tópico '{topico}' enviado.\n")
        self.txt_feed.see(tk.END)
        self.entry_topico_sub.delete(0, tk.END)

    def acao_publicar(self):
        if not self.cliente.topicos_inscritos:
            messagebox.showerror("Acesso Negado", "Bloqueado: Você precisa se inscrever em ao menos um tópico antes de realizar publicações.")
            return
            
        topico = self.entry_topico_pub.get().strip()
        mensagem = self.entry_mensagem.get().strip()
        
        if not topico or not mensagem:
            # Mantendo suporte para variáveis internas caso utilize 'mensagem' ou 'message'
            pass
        
        if not topico or not mensagem:
            messagebox.showwarning("Campos Vazios", "Por favor, preencha o Tópico Alvo e a Mensagem.")
            return
            
        self.cliente.publicar(topico, mensagem)
        self.txt_feed.insert(tk.END, f"📤 [Você -> '{topico}']: {mensagem}\n")
        self.txt_feed.see(tk.END)
        self.entry_mensagem.delete(0, tk.END)

    def atualizar_feed_mensagens(self, topico, mensagem, remetente="Desconhecido"):
        # Intercepta o sinal do broker e aciona o método que você criou para atualizar a Label
        if topico == "SISTEMA" and "Sessão restaurada!" in mensagem:
            self.atualizar_label_topicos()
            
        # Formatação das mensagens dentro do Feed escuro
        if topico == "SISTEMA" or remetente == "BROKER":
            texto_formatado = f"⚙️ [SISTEMA]: {mensagem}\n"
        else:
            texto_formatado = f"💬 [{remetente} @ '{topico}']: {mensagem}\n"
            
        self.txt_feed.insert(tk.END, texto_formatado)
        self.txt_feed.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ClienteGUI(root)
    root.mainloop()