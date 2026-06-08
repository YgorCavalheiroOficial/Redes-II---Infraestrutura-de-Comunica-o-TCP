import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog
import threading
from cliente.aplicacao_cliente import Cliente

class ClienteGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Pub/Sub Client - Dashboard")
        self.root.geometry("600x550")
        self.root.configure(bg="#f0f2f5")
        
        # Inicializa o cliente padrão do seu projeto
        self.cliente = Cliente(broker_host='127.0.0.1', broker_port=1024)
        
        # Construção da Interface
        self.criar_widgets()
        
        # Conecta automaticamente ao iniciar
        self.conectar_ao_broker()

    def criar_widgets(self):
        # --- HEADER / STATUS ---
        self.frame_status = tk.LabelFrame(self.root, text=" Status da Conexão ", bg="#f0f2f5", font=("Arial", 10, "bold"))
        self.frame_status.pack(fill="x", padx=15, pady=10)
        
        self.lbl_status = tk.Label(self.frame_status, text="Tentando conexão...", fg="orange", bg="#f0f2f5", font=("Arial", 11, "bold"))
        self.lbl_status.pack(pady=5)

        # --- SEÇÃO DE INSCRIÇÃO (SUBSCRIBE / UNSUBSCRIBE) ---
        self.frame_sub = tk.LabelFrame(self.root, text=" Gerenciar Inscrições ", bg="#f0f2f5", font=("Arial", 10, "bold"))
        self.frame_sub.pack(fill="x", padx=15, pady=5)
        
        tk.Label(self.frame_sub, text="Tópico:", bg="#f0f2f5").grid(row=0, column=0, padx=5, pady=10, sticky="w")
        self.entry_topico_sub = tk.Entry(self.frame_sub, width=25, font=("Arial", 10))
        self.entry_topico_sub.grid(row=0, column=1, padx=5, pady=10)
        
        self.btn_sub = tk.Button(self.frame_sub, text="Inscrever", bg="#4CAF50", fg="white", font=("Arial", 9, "bold"), command=self.acao_inscrever)
        self.btn_sub.grid(row=0, column=2, padx=5, pady=10)
        
        self.btn_unsub = tk.Button(self.frame_sub, text="Desinscrever", bg="#f44336", fg="white", font=("Arial", 9, "bold"), command=self.acao_desinscrever)
        self.btn_unsub.grid(row=0, column=3, padx=5, pady=10)
        
        self.lbl_meus_topicos = tk.Label(self.frame_sub, text="Inscrito em: nenhume", fg="#555", bg="#f0f2f5", font=("Arial", 9, "italic"))
        self.lbl_meus_topicos.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="w")

        # --- SEÇÃO DE PUBLICAÇÃO (PUBLISH) ---
        self.frame_pub = tk.LabelFrame(self.root, text=" Publicar Mensagem ", bg="#f0f2f5", font=("Arial", 10, "bold"))
        self.frame_pub.pack(fill="x", padx=15, pady=5)
        
        tk.Label(self.frame_pub, text="Tópico alvo:", bg="#f0f2f5").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_topico_pub = tk.Entry(self.frame_pub, width=25, font=("Arial", 10))
        self.entry_topico_pub.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(self.frame_pub, text="Mensagem:", bg="#f0f2f5").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_mensagem = tk.Entry(self.frame_pub, width=40, font=("Arial", 10))
        self.entry_mensagem.grid(row=1, column=1, columnspan=2, padx=5, pady=5)
        
        self.btn_pub = tk.Button(self.frame_pub, text="Enviar Mensagem", bg="#2196F3", fg="white", font=("Arial", 9, "bold"), command=self.acao_publicar)
        self.btn_pub.grid(row=1, column=3, padx=5, pady=5)

        # --- PAINEL DE MONITORAMENTO (MENSAGENS RECEBIDAS) ---
        self.frame_monitor = tk.LabelFrame(self.root, text=" Feed de Mensagens Recebidas ", bg="#f0f2f5", font=("Arial", 10, "bold"))
        self.frame_monitor.pack(fill="both", expand=True, padx=15, pady=10)
        
        self.txt_feed = scrolledtext.ScrolledText(self.frame_monitor, bg="black", fg="#00FF00", font=("Consolas", 10))
        self.txt_feed.pack(fill="both", expand=True, padx=5, pady=5)

    # Importe o simpledialog no topo do main_gui.py: from tkinter import simpledialog

    def conectar_ao_broker(self):
        # Abre um popup bonitinho perguntando quem é o usuário antes de conectar
        client_id = tk.simpledialog.askstring("Identidade do Cliente", "Digite o seu nome/ID único:")
        
        if not client_id:
            messagebox.showerror("Erro", "Você precisa digitar um ID para usar o sistema.")
            self.root.destroy()
            return

        try:
            self.root.title(f"Pub/Sub Client - Logado como: {client_id}")
            self.cliente.conectar(client_id) # Passa o ID aqui
            self.lbl_status.config(text=f"● CONECTADO COMO {client_id.upper()}", fg="green")
            
            thread_escuta = threading.Thread(target=self.cliente.escutar, args=(self.atualizar_feed_mensagens,), daemon=True)
            thread_escuta.start()
        except Exception as e:
            self.lbl_status.config(text="● FALHA AO CONECTAR", fg="red")
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar:\n{e}")

    # Atualize também a função que desenha o texto na tela preta para mostrar o remetente:
    def atualizar_feed_mensagens(self, topico, message, remetente):
        self.txt_feed.insert(tk.END, f"[{remetente} @ '{topico}']: {message}\n")
        self.txt_feed.see(tk.END)

    def atualizar_label_topicos(self):
        lista_topicos = list(self.cliente.topicos_inscritos)
        if lista_topicos:
            self.lbl_meus_topicos.config(text=f"Inscrito em: {', '.join(lista_topicos)}", fg="blue")
        else:
            self.lbl_meus_topicos.config(text="Inscrito em: nenhum", fg="#555")

    def acao_inscrever(self):
        topico = self.entry_topico_sub.get().strip()
        if not topico:
            messagebox.showwarning("Campo Vazio", "Digite um tópico para se inscrever.")
            return
        
        self.cliente.inscrever(topico)
        self.atualizar_label_topicos()
        self.txt_feed.insert(tk.END, f"[SISTEMA] Inscrição enviada para o tópico: '{topico}'\n")
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
        self.txt_feed.insert(tk.END, f"[SISTEMA] Cancelamento do tópico '{topico}' enviado.\n")
        self.entry_topico_sub.delete(0, tk.END)

    def acao_publicar(self):
        # 🔴 TRAVA DE SEGURANÇA VISUAL: Só publica se estiver inscrito em algo
        if not self.cliente.topicos_inscritos:
            messagebox.showerror("Acesso Negado", "Bloqueado: Você precisa se inscrever em ao menos um tópico antes de realizar publicações.")
            return
            
        topico = self.entry_topico_pub.get().strip()
        mensagem = self.entry_mensagem.get().strip()
        
        if not topico or not mensagem:
            messagebox.showwarning("Campos Vazios", "Por favor, preencha o Tópico Alvo e a Mensagem.")
            return
            
        self.cliente.publicar(topico, mensagem)
        self.txt_feed.insert(tk.END, f"[PUB] Enviado para '{topico}': {mensagem}\n")
        self.entry_mensagem.delete(0, tk.END)

    def atualizar_feed_mensagens(self, topico, mensagem, remetente="Desconhecido"):
        # Se for o aviso de restauração, atualiza visualmente sua lista de tópicos
        if topico == "SISTEMA" and "Sessão restaurada!" in mensagem:
            # 🔴 ATENÇÃO: Substitua 'self.listbox_topicos' pelo nome real do seu componente visual de lista de tópicos
            self.atualizar_label_topicos()
            
        # Mantém a inserção normal de texto no feed do chat
        texto_formatado = f"[{remetente} @ '{topico}']: {mensagem}\n"
        self.txt_feed.insert(tk.END, texto_formatado)
        self.txt_feed.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ClienteGUI(root)
    root.mainloop()