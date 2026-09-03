import streamlit as st
import sqlite3
import pandas as pd
import datetime
from fpdf import FPDF

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="CL Artes - Gestão, Precificação & PDV",
    page_icon="🖨️",
    layout="wide"
)

DB_NAME = "sistema_dtf_v2.db"

# ---------------------------------------------------------
# ESTRUTURA DO BANCO DE DADOS (SQLITE)
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Tabela de Clientes
    c.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa TEXT,
            tipo_pessoa TEXT,
            responsavel TEXT NOT NULL,
            telefone TEXT,
            email TEXT,
            pref_contato TEXT,
            data_cadastro TEXT
        )
    ''')
    
    # 2. Tabela de Orçamentos
    c.execute('''
        CREATE TABLE IF NOT EXISTS orcamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            data TEXT,
            total_itens INTEGER,
            ocupacao_folha REAL,
            valor_total REAL,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')

    # 3. Tabela de Produtos / Serviços do PDV
    c.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT,
            preco REAL NOT NULL,
            estoque INTEGER DEFAULT 0
        )
    ''')

    # 4. Tabela de Vendas (PDV)
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            data TEXT,
            forma_pagamento TEXT,
            subtotal REAL,
            desconto REAL,
            total REAL,
            itens_detalhe TEXT,
            link_pagamento TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')
    
    # Adiciona a coluna link_pagamento se a tabela já existir de execuções anteriores
    c.execute("PRAGMA table_info(vendas)")
    cols = [col[1] for col in c.fetchall()]
    if "link_pagamento" not in cols:
        c.execute("ALTER TABLE vendas ADD COLUMN link_pagamento TEXT")

    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# FUNÇÕES DE BANCO DE DADOS
# ---------------------------------------------------------
def cadastrar_cliente(empresa, tipo_pessoa, responsavel, telefone, email, pref_contato):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    c.execute('''
        INSERT INTO clientes (empresa, tipo_pessoa, responsavel, telefone, email, pref_contato, data_cadastro)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (empresa, tipo_pessoa, responsavel, telefone, email, pref_contato, hoje))
    conn.commit()
    conn.close()

def listar_clientes():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('''
        SELECT id, empresa AS 'Empresa', tipo_pessoa AS 'Tipo', responsavel AS 'Responsável', 
               telefone AS 'Telefone/Whats', email AS 'E-mail', pref_contato AS 'Contato Pref.', 
               data_cadastro AS 'Data Cadastro' 
        FROM clientes 
        ORDER BY responsavel ASC
    ''', conn)
    conn.close()
    return df

def salvar_orcamento_db(cliente_id, total_itens, ocupacao, valor_total):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    c.execute('''
        INSERT INTO orcamentos (cliente_id, data, total_itens, ocupacao_folha, valor_total)
        VALUES (?, ?, ?, ?, ?)
    ''', (cliente_id, hoje, total_itens, ocupacao, valor_total))
    conn.commit()
    conn.close()

def buscar_pedidos_cliente(cliente_id):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('''
        SELECT id AS 'Nº Pedido', data AS 'Data/Hora', total_itens AS 'Qtd Itens', 
               ocupacao_folha AS 'Ocupação (%)', valor_total AS 'Valor Total (R$)' 
        FROM orcamentos 
        WHERE cliente_id = ? 
        ORDER BY id DESC
    ''', conn, params=(cliente_id,))
    conn.close()
    return df

def buscar_vendas_cliente(cliente_id):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('''
        SELECT id AS 'Nº Venda PDV', data AS 'Data/Hora', forma_pagamento AS 'Forma Pagamento', 
               itens_detalhe AS 'Itens Comprados', total AS 'Valor Total (R$)', link_pagamento AS 'Link/Obs'
        FROM vendas 
        WHERE cliente_id = ? 
        ORDER BY id DESC
    ''', conn, params=(cliente_id,))
    conn.close()
    return df

# --- Funções do PDV ---
def cadastrar_produto(nome, categoria, preco, estoque):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO produtos (nome, categoria, preco, estoque)
        VALUES (?, ?, ?, ?)
    ''', (nome, categoria, preco, estoque))
    conn.commit()
    conn.close()

def listar_produtos():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('''
        SELECT id, nome AS 'Produto/Serviço', categoria AS 'Categoria', 
               preco AS 'Preço (R$)', estoque AS 'Estoque' 
        FROM produtos 
        ORDER BY nome ASC
    ''', conn)
    conn.close()
    return df

def registrar_venda(cliente_id, forma_pagamento, subtotal, desconto, total, itens_str, link_pagto=""):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    c.execute('''
        INSERT INTO vendas (cliente_id, data, forma_pagamento, subtotal, desconto, total, itens_detalhe, link_pagamento)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (cliente_id, agora, forma_pagamento, subtotal, desconto, total, itens_str, link_pagto))
    conn.commit()
    conn.close()

def listar_vendas():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('''
        SELECT v.id AS 'Nº Venda', v.data AS 'Data/Hora', 
               COALESCE(c.responsavel, 'Cliente Avulso') AS 'Cliente',
               v.forma_pagamento AS 'Pagamento', v.subtotal AS 'Subtotal (R$)',
               v.desconto AS 'Desconto (R$)', v.total AS 'Total (R$)',
               v.itens_detalhe AS 'Itens', COALESCE(v.link_pagamento, '') AS 'Link/Obs'
        FROM vendas v
        LEFT JOIN clientes c ON v.cliente_id = c.id
        ORDER BY v.id DESC
    ''', conn)
    conn.close()
    return df


# ---------------------------------------------------------
# MENU LATERAL DE NAVEGAÇÃO
# ---------------------------------------------------------
st.sidebar.title("📌 Menu Principal")
menu_opcao = st.sidebar.radio(
    "Navegação",
    ["👤 Cadastro de Clientes", "🧮 Calcular Preço DTF", "🛒 PDV (Ponto de Venda)"],
    index=0
)

st.sidebar.divider()

# =========================================================
# MENU 1: CADASTRO E HISTÓRICO DE CLIENTES
# =========================================================
if menu_opcao == "👤 Cadastro de Clientes":
    st.title("👤 Gestão de Clientes e Histórico de Pedidos")

    tab_cad, tab_list = st.tabs(["➕ Cadastrar Novo Cliente", "📋 Lista & Histórico de Clientes"])

    with tab_cad:
        st.subheader("Formulário de Cadastro")
        with st.form("form_cliente", clear_on_submit=True):
            col_emp, col_tipo = st.columns([3, 1])
            with col_emp:
                empresa = st.text_input("Nome da Empresa / Marca")
            with col_tipo:
                tipo_pessoa = st.selectbox("Tipo de Cadastro", ["Pessoa Física (CPF)", "Pessoa Jurídica (CNPJ)"])

            col_resp, col_tel = st.columns(2)
            with col_resp:
                responsavel = st.text_input("Nome do Responsável *")
            with col_tel:
                telefone = st.text_input("Telefone / WhatsApp")

            col_email, col_pref = st.columns([2, 1])
            with col_email:
                email = st.text_input("E-mail")
            with col_pref:
                pref_contato = st.selectbox("Preferência de Contato", ["WhatsApp", "E-mail"])

            btn_cadastrar = st.form_submit_button("💾 Salvar Cadastro")
            if btn_cadastrar:
                if responsavel.strip() == "":
                    st.error("O nome do responsável é obrigatório!")
                else:
                    cadastrar_cliente(empresa, tipo_pessoa, responsavel, telefone, email, pref_contato)
                    st.success(f"Cliente '{responsavel}' cadastrado com sucesso!")
                    st.rerun()

    with tab_list:
        df_clientes = listar_clientes()
        if df_clientes.empty:
            st.info("Nenhum cliente cadastrado ainda.")
        else:
            st.subheader("Clientes Cadastrados")

            col_busca, _ = st.columns([2, 1])
            with col_busca:
                termo_busca = st.text_input("🔍 Buscar cliente por Nome ou Empresa:", placeholder="Digite o nome ou empresa...")

            if termo_busca.strip():
                df_filtrado = df_clientes[
                    df_clientes['Responsável'].fillna('').str.contains(termo_busca, case=False, na=False) |
                    df_clientes['Empresa'].fillna('').str.contains(termo_busca, case=False, na=False)
                ]
            else:
                df_filtrado = df_clientes

            st.dataframe(df_filtrado, use_container_width=True)

            if df_filtrado.empty:
                st.warning(f"Nenhum cliente encontrado com a busca '{termo_busca}'.")

            st.divider()
            st.subheader("📜 Consultar Histórico do Cliente")
            
            cliente_dict_hist = {
                f"{row['Responsável']} " + (f"({row['Empresa']})" if row['Empresa'] else "") + f" - ID: {row['id']}": row['id'] 
                for _, row in df_filtrado.iterrows()
            }

            if cliente_dict_hist:
                cli_selecionado = st.selectbox("Selecione um cliente para ver o histórico completo:", list(cliente_dict_hist.keys()))
                
                if cli_selecionado:
                    c_id = cliente_dict_hist[cli_selecionado]
                    
                    tab_hist_vendas_cli, tab_hist_orc = st.tabs(["🛒 Vendas do PDV", "🧮 Orçamentos Calculados"])
                    
                    with tab_hist_vendas_cli:
                        df_vendas_cli = buscar_vendas_cliente(c_id)
                        if df_vendas_cli.empty:
                            st.write("Nenhuma venda realizada no PDV para este cliente.")
                        else:
                            st.dataframe(df_vendas_cli, use_container_width=True)
                            total_comprado = df_vendas_cli['Valor Total (R$)'].sum()
                            st.success(f"💰 Total faturado em vendas PDV com este cliente: **R$ {total_comprado:.2f}**")

                    with tab_hist_orc:
                        df_pedidos = buscar_pedidos_cliente(c_id)
                        if df_pedidos.empty:
                            st.write("Nenhum orçamento gravado para este cliente.")
                        else:
                            st.dataframe(df_pedidos, use_container_width=True)
                            total_gasto = df_pedidos['Valor Total (R$)'].sum()
                            st.info(f"💰 Total acumulado em orçamentos deste cliente: **R$ {total_gasto:.2f}**")

# =========================================================
# MENU 2: CALCULAR PREÇO DTF
# =========================================================
elif menu_opcao == "🧮 Calcular Preço DTF":
    st.title("🖨️ Precificadora de Artes DTF")
    st.write("Monte orçamentos com múltiplos itens na folha de 1m x 40cm.")

    LARGURA_FOLHA_CM = 40.0
    COMPRIMENTO_FOLHA_CM = 100.0
    VALOR_FOLHA_RS = 79.90
    AREA_FOLHA_CM2 = LARGURA_FOLHA_CM * COMPRIMENTO_FOLHA_CM
    CUSTO_CM2 = VALOR_FOLHA_RS / AREA_FOLHA_CM2

    st.sidebar.header("⚙️ Configurações de Venda")
    markup = st.sidebar.slider("Margem de Lucro (%)", min_value=0, max_value=200, value=30, step=5)
    taxa_arquivo = st.sidebar.number_input("Taxa Fixa / Edição (R$)", min_value=0.0, value=5.0, step=1.0)

    df_cli = listar_clientes()
    if not df_cli.empty:
        clientes_dict = {
            f"{row['Responsável']} " + (f"({row['Empresa']})" if row['Empresa'] else ""): row['id'] 
            for _, row in df_cli.iterrows()
        }
        cliente_selecionado_str = st.sidebar.selectbox("Selecione o Cliente", list(clientes_dict.keys()))
        cliente_id_atual = clientes_dict[cliente_selecionado_str]
        nome_cliente_atual = cliente_selecionado_str
    else:
        st.sidebar.warning("⚠️ Nenhum cliente cadastrado. Acesse o menu 'Cadastro de Clientes'.")
        nome_cliente_atual = st.sidebar.text_input("Nome do Cliente (Avulso)", value="Cliente Exemplo")
        cliente_id_atual = None

    if "itens_orcamento" not in st.session_state:
        st.session_state.itens_orcamento = []

    st.subheader("📐 Adicionar Item ao Orçamento")
    col_nome, col_qtd = st.columns([2, 1])
    with col_nome:
        nome_item = st.text_input("Descrição do Desenho", value="Estampa A4 Camiseta")
    with col_qtd:
        qtd_item = st.number_input("Quantidade", min_value=1, value=1, step=1)

    col_w, col_h = st.columns(2)
    with col_w:
        largura_item = st.number_input("Largura (cm)", min_value=0.1, value=21.0, step=0.5)
    with col_h:
        altura_item = st.number_input("Comprimento (cm)", min_value=0.1, value=29.7, step=0.5)

    if st.button("➕ Adicionar Item ao Pedido"):
        area_un = largura_item * altura_item
        area_total_item = area_un * qtd_item
        custo_base_item = area_total_item * CUSTO_CM2
        preco_venda_item = custo_base_item * (1 + (markup / 100))
        
        st.session_state.itens_orcamento.append({
            "nome": nome_item,
            "qtd": qtd_item,
            "largura": largura_item,
            "altura": altura_item,
            "area_total": area_total_item,
            "preco_total": preco_venda_item
        })
        st.success(f"Item '{nome_item}' adicionado!")

    st.divider()

    st.subheader("🛒 Itens no Orçamento")
    if len(st.session_state.itens_orcamento) == 0:
        st.info("Nenhum item adicionado ao orçamento.")
    else:
        area_total_acumulada = 0.0
        subtotal_impressao = 0.0
        
        for i, item in enumerate(st.session_state.itens_orcamento):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.write(f"**{item['qtd']}x {item['nome']}**")
            c2.write(f"{item['largura']}x{item['altura']} cm")
            c3.write(f"R$ {item['preco_total']:.2f}")
            if c4.button("❌", key=f"del_{i}"):
                st.session_state.itens_orcamento.pop(i)
                st.rerun()
            
            area_total_acumulada += item["area_total"]
            subtotal_impressao += item["preco_total"]

        porcentagem_total_folha = (area_total_acumulada / AREA_FOLHA_CM2) * 100
        valor_total_pedido = subtotal_impressao + taxa_arquivo

        st.divider()
        st.subheader("📊 Resumo Financeiro")
        m1, m2, m3 = st.columns(3)
        m1.metric("Ocupação do Metro", f"{porcentagem_total_folha:.2f}%")
        m2.metric("Subtotal Impressão", f"R$ {subtotal_impressao:.2f}")
        m3.metric("Total Final (com taxa)", f"R$ {valor_total_pedido:.2f}")

        if porcentagem_total_folha > 100:
            st.warning(f"⚠️ Os itens ocupam {porcentagem_total_folha:.1f}% da folha (será necessário mais de 1 metro).")

        col_pdf, col_save, col_clear = st.columns(3)

        class PDF(FPDF):
            def header(self):
                self.set_fill_color(249, 243, 234)
                self.rect(0, 0, 210, 38, 'F')
                try:
                    self.image("logo.jpg", x=10, y=4, w=30)
                    pos_x = 45
                except:
                    pos_x = 10
                self.set_font('Helvetica', 'B', 15)
                self.set_text_color(26, 26, 26)
                self.set_xy(pos_x, 10)
                self.cell(0, 8, 'ORCAMENTO DE IMPRESSAO DTF', ln=True)
                self.set_font('Helvetica', 'B', 10)
                self.set_text_color(0, 163, 224)
                self.set_x(pos_x)
                self.cell(0, 5, 'CL ARTES - SUA IDEIA EM DTF', ln=True)
                self.ln(12)

            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'B', 8)
                self.set_text_color(230, 0, 126)
                self.cell(0, 10, 'CL Artes - Sua ideia em DTF | Obrigado pela preferencia!', align='C')

        def gerar_pdf():
            pdf = PDF()
            pdf.add_page()
            hoje = datetime.date.today().strftime("%d/%m/%Y")

            pdf.set_font('Helvetica', 'B', 12)
            pdf.set_text_color(26, 26, 26)
            pdf.cell(0, 8, 'Dados do Pedido', ln=True)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(100, 6, f'Cliente: {nome_cliente_atual}')
            pdf.cell(0, 6, f'Data: {hoje}', ln=True)
            pdf.ln(4)

            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 8, 'Especificacoes das Artes', ln=True)
            pdf.set_fill_color(26, 26, 26)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(15, 7, 'Qtd', 1, 0, 'C', True)
            pdf.cell(70, 7, 'Item / Descricao', 1, 0, 'L', True)
            pdf.cell(40, 7, 'Dimensoes', 1, 0, 'C', True)
            pdf.cell(30, 7, '% Ocupada', 1, 0, 'C', True)
            pdf.cell(35, 7, 'Valor (R$)', 1, 1, 'R', True)

            pdf.set_text_color(26, 26, 26)
            pdf.set_font('Helvetica', '', 9)
            for item in st.session_state.itens_orcamento:
                pct = (item['area_total'] / AREA_FOLHA_CM2) * 100
                pdf.cell(15, 7, str(item['qtd']), 1, 0, 'C')
                pdf.cell(70, 7, item['nome'][:35], 1, 0, 'L')
                pdf.cell(40, 7, f"{item['largura']} x {item['altura']} cm", 1, 0, 'C')
                pdf.cell(30, 7, f"{pct:.1f}%", 1, 0, 'C')
                pdf.cell(35, 7, f"R$ {item['preco_total']:.2f}", 1, 1, 'R')

            pdf.ln(6)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 8, 'Resumo Financeiro', ln=True)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(130, 7, 'Subtotal das Impressoes:', 1)
            pdf.cell(60, 7, f'R$ {subtotal_impressao:.2f}', 1, 1, 'R')
            pdf.cell(130, 7, 'Taxa de Preparacao / Edicao:', 1)
            pdf.cell(60, 7, f'R$ {taxa_arquivo:.2f}', 1, 1, 'R')

            pdf.set_fill_color(249, 243, 234)
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(230, 0, 126)
            pdf.cell(130, 8, 'VALOR TOTAL DO ORCAMENTO:', 1, 0, 'L', True)
            pdf.cell(60, 8, f'R$ {valor_total_pedido:.2f}', 1, 1, 'R', True)

            return bytes(pdf.output())

        with col_pdf:
            pdf_bytes = gerar_pdf()
            st.download_button("📥 Baixar PDF", pdf_bytes, file_name=f"Orcamento_{nome_cliente_atual}.pdf", mime="application/pdf", use_container_width=True)

        with col_save:
            if st.button("💾 Salvar no Historico", use_container_width=True):
                if cliente_id_atual:
                    salvar_orcamento_db(cliente_id_atual, len(st.session_state.itens_orcamento), porcentagem_total_folha, valor_total_pedido)
                    st.success("Orçamento vinculado e salvo com sucesso!")
                else:
                    st.error("Cadastre o cliente para salvar o histórico no banco.")

        with col_clear:
            if st.button("🗑️ Limpar Lista", use_container_width=True):
                st.session_state.itens_orcamento = []
                st.rerun()

# =========================================================
# MENU 3: PDV (PONTO DE VENDA)
# =========================================================
elif menu_opcao == "🛒 PDV (Ponto de Venda)":
    st.title("🛒 Ponto de Venda (PDV) - Caixa")

    tab_venda, tab_prod, tab_hist_vendas = st.tabs(["💳 Frente de Caixa", "📦 Cadastrar Produtos/Serviços", "📊 Histórico Geral de Vendas"])

    # -----------------------------------------------------
    # ABA 1: FRENTE DE CAIXA
    # -----------------------------------------------------
    with tab_venda:
        if "carrinho_pdv" not in st.session_state:
            st.session_state.carrinho_pdv = []

        df_prods = listar_produtos()
        df_clis = listar_clientes()

        col_esq, col_dir = st.columns([3, 2])

        # Coluna Esquerda: Adicionar Itens ao Caixa
        with col_esq:
            st.subheader("1. Adicionar ao Carrinho")
            
            modo_item = st.radio("Origem do Item:", ["Produto do Estoque/Catálogo", "Serviço/Item Avulso"], horizontal=True)

            if modo_item == "Produto do Estoque/Catálogo":
                if df_prods.empty:
                    st.warning("Nenhum produto cadastrado. Vá na aba 'Cadastrar Produtos' para adicionar.")
                else:
                    prod_dict = {f"{row['Produto/Serviço']} (R$ {row['Preço (R$)']:.2f})": row for _, row in df_prods.iterrows()}
                    prod_sel_nome = st.selectbox("Selecione o Produto:", list(prod_dict.keys()))
                    prod_sel = prod_dict[prod_sel_nome]

                    col_q, col_b = st.columns([1, 2])
                    with col_q:
                        qtd_pdv = st.number_input("Qtd", min_value=1, value=1, step=1)
                    with col_b:
                        st.write("") 
                        if st.button("➕ Adicionar ao Carrinho"):
                            st.session_state.carrinho_pdv.append({
                                "nome": prod_sel["Produto/Serviço"],
                                "preco_un": prod_sel["Preço (R$)"],
                                "qtd": qtd_pdv,
                                "total": prod_sel["Preço (R$)"] * qtd_pdv
                            })
                            st.success("Item adicionado!")
                            st.rerun()

            else: # Item Avulso
                col_a1, col_a2, col_a3 = st.columns([3, 1, 1])
                with col_a1:
                    nome_avulso = st.text_input("Descrição do Item/Serviço", value="Impressão DTF Metro")
                with col_a2:
                    preco_avulso = st.number_input("Preço Un. (R$)", min_value=0.0, value=79.90, step=5.0)
                with col_a3:
                    qtd_avulso = st.number_input("Qtd ", min_value=1, value=1, step=1)

                if st.button("➕ Adicionar Item Avulso"):
                    st.session_state.carrinho_pdv.append({
                        "nome": nome_avulso,
                        "preco_un": preco_avulso,
                        "qtd": qtd_avulso,
                        "total": preco_avulso * qtd_avulso
                    })
                    st.success("Item avulso adicionado!")
                    st.rerun()

            st.divider()
            st.subheader("📋 Itens no Caixa")
            if not st.session_state.carrinho_pdv:
                st.info("Carrinho vazio.")
            else:
                for idx, item_c in enumerate(st.session_state.carrinho_pdv):
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    c1.write(f"**{item_c['nome']}**")
                    c2.write(f"{item_c['qtd']}x R${item_c['preco_un']:.2f}")
                    c3.write(f"**R$ {item_c['total']:.2f}**")
                    if c4.button("❌", key=f"pdv_del_{idx}"):
                        st.session_state.carrinho_pdv.pop(idx)
                        st.rerun()

        # Coluna Direita: Seleção de Cliente e Fechamento
        with col_dir:
            st.subheader("2. Cliente e Pagamento")
            
            # Seleção de Cliente Obrigatória/Sugerida
            cliente_venda_id = None
            if df_clis.empty:
                st.warning("⚠️ Nenhum cliente cadastrado. A venda será como 'Cliente Avulso'.")
            else:
                cli_venda_dict = {"👤 Cliente Avulso (Não cadastrado)": None}
                for _, row in df_clis.iterrows():
                    emp_str = f" ({row['Empresa']})" if row['Empresa'] else ""
                    cli_venda_dict[f"👤 {row['Responsável']}{emp_str}"] = row['id']
                
                cli_venda_sel = st.selectbox("Selecione o Cliente para a Venda *", list(cli_venda_dict.keys()))
                cliente_venda_id = cli_venda_dict[cli_venda_sel]

            # Seleção de Pagamento
            forma_pagto = st.selectbox(
                "Forma de Pagamento *", 
                ["Pix", "Dinheiro", "Link de Pagamento"]
            )

            link_pagto_input = ""
            if forma_pagto == "Link de Pagamento":
                link_pagto_input = st.text_input("Insira o Link de Pagamento (Mercado Pago, Asaas, etc.):", placeholder="https://...")

            # Cálculos do Caixa
            subtotal_venda = sum(item['total'] for item in st.session_state.carrinho_pdv)
            desconto_venda = st.number_input("Desconto (R$):", min_value=0.0, max_value=subtotal_venda if subtotal_venda > 0 else 0.0, value=0.0, step=1.0)
            total_final_venda = subtotal_venda - desconto_venda

            st.divider()
            st.metric("Subtotal", f"R$ {subtotal_venda:.2f}")
            st.metric("Total Final a Pagar", f"R$ {total_final_venda:.2f}")

            if st.button("✅ Finalizar Venda", type="primary", use_container_width=True):
                if not st.session_state.carrinho_pdv:
                    st.error("Adicione ao menos um item ao carrinho antes de finalizar!")
                else:
                    itens_str = ", ".join([f"{i['qtd']}x {i['nome']}" for i in st.session_state.carrinho_pdv])
                    
                    registrar_venda(cliente_venda_id, forma_pagto, subtotal_venda, desconto_venda, total_final_venda, itens_str, link_pagto_input)
                    
                    st.balloons()
                    st.success("🎉 Venda concluída e vinculada ao histórico!")
                    st.session_state.carrinho_pdv = []
                    st.rerun()

    # -----------------------------------------------------
    # ABA 2: CADASTRAR PRODUTOS/SERVIÇOS
    # -----------------------------------------------------
    with tab_prod:
        st.subheader("➕ Cadastrar Novo Produto ou Serviço no Catálogo")
        with st.form("form_produto", clear_on_submit=True):
            col_p1, col_p2 = st.columns([2, 1])
            with col_p1:
                nome_p = st.text_input("Nome do Produto / Serviço *")
            with col_p2:
                categoria_p = st.selectbox("Categoria", ["Impressão DTF", "Insumo/Material", "Camisetas", "Acessórios", "Outros"])

            col_p3, col_p4 = st.columns(2)
            with col_p3:
                preco_p = st.number_input("Preço de Venda (R$)", min_value=0.0, value=10.0, step=1.0)
            with col_p4:
                estoque_p = st.number_input("Estoque Inicial (Qtd)", min_value=0, value=100, step=1)

            btn_prod = st.form_submit_button("💾 Salvar Produto")
            if btn_prod:
                if nome_p.strip() == "":
                    st.error("O nome do produto é obrigatório!")
                else:
                    cadastrar_produto(nome_p, categoria_p, preco_p, estoque_p)
                    st.success(f"Produto '{nome_p}' cadastrado com sucesso!")
                    st.rerun()

        st.divider()
        st.subheader("📦 Produtos e Serviços Cadastrados")
        df_p_list = listar_produtos()
        if df_p_list.empty:
            st.info("Nenhum produto cadastrado.")
        else:
            st.dataframe(df_p_list, use_container_width=True)

    # -----------------------------------------------------
    # ABA 3: HISTÓRICO GERAL DE VENDAS
    # -----------------------------------------------------
    with tab_hist_vendas:
        st.subheader("📊 Relatório Geral de Vendas do Caixa")
        df_vendas = listar_vendas()

        if df_vendas.empty:
            st.info("Nenhuma venda registrada ainda.")
        else:
            t_faturamento = df_vendas['Total (R$)'].sum()
            t_vendas_count = len(df_vendas)

            m_v1, m_v2 = st.columns(2)
            m_v1.metric("Faturamento Total acumulado", f"R$ {t_faturamento:.2f}")
            m_v2.metric("Total de Vendas Realizadas", f"{t_vendas_count}")

            st.divider()
            st.dataframe(df_vendas, use_container_width=True)