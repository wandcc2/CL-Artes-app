import streamlit as st
import pandas as pd
import sqlite3
import math
import os
from datetime import datetime
from fpdf import FPDF

# ==========================================
# CONFIGURAÇÃO INICIAL E ESTILO
# ==========================================
st.set_page_config(
    page_title="CL Artes - Gestão & Precificação",
    page_icon="🎨",
    layout="wide"
)

DB_NAME = 'sistema_cl_artes.db'

# Estilo CSS Personalizado
st.markdown("""
<style>
    .main-title {
        color: #1E3A8A;
        font-size: 2.2rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #F3F4F6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1E3A8A;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# TABELAS FIXAS DE QUANTIDADES E PREÇOS
# ==========================================
OPCOES_TABELA = {
    "CHAVEIRO CORDÃO (Poliéster Acetinado 20mm - Colorido Frente e Verso - 11x2cm)": {
        30: 9.17,
        60: 8.75,
        90: 8.33
    },
    "CHAVEIRO ABRIDOR (Ferro - Gravação a Laser - 3,8x0,7cm)": {
        10: 4.17,
        20: 3.92,
        50: 3.83,
        100: 3.75,
        250: 3.71,
        500: 3.67,
        1000: 3.50
    }
}

# ==========================================
# CLASSE PARA GERAÇÃO DO PDF DE ORÇAMENTO
# ==========================================
class PDFOrcamento(FPDF):
    def add_page(self, orientation='', format='', same_pagedim=False):
        super().add_page(orientation, format, same_pagedim)
        # Preenche o fundo de toda a página com o bege da logo (RGB: 247, 243, 238)
        self.set_fill_color(247, 243, 238)
        self.rect(0, 0, self.w, self.h, 'F')

    def header(self):
        # Inclusão da logo se existir no diretório
        if os.path.exists("logo.jpg"):
            self.image("logo.jpg", 10, 8, 33)
            self.set_x(48)
            self.set_font("Helvetica", "B", 16)
            self.cell(0, 10, "CL ARTES - PERSONALIZADOS", ln=True)
            self.set_x(48)
            self.set_font("Helvetica", "", 10)
            self.cell(0, 5, "Orçamentos e Comprovantes de Pedido", ln=True)
            self.ln(10)
        else:
            self.set_font("Helvetica", "B", 18)
            self.cell(0, 10, "CL ARTES - PERSONALIZADOS", ln=True, align="C")
            self.ln(5)

    def footer(self):
        self.set_y(-25)
        self.set_font("Helvetica", "I", 8)
        self.multi_cell(0, 4, 
            "Aviso Importante: Este orçamento tem validade de 3 (três) dias a contar da data de sua emissão. "
            "Os valores finais podem variar de acordo com a taxa de frete e local de entrega.", 
            align="C"
        )
        self.ln(2)
        self.cell(0, 5, f"Página {self.page_no()}", align="C")

def gerar_pdf_bytes(cliente_nome, cliente_contato, itens, valor_total):
    pdf = PDFOrcamento()
    pdf.add_page()
    
    # Título do Documento
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "ORÇAMENTO DE PRODUTOS", ln=True, align="C")
    pdf.ln(3)
    
    # Dados do Cliente e Data
    pdf.set_font("Helvetica", "", 10)
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.cell(0, 6, f"Data de Emissão: {data_atual}", ln=True)
    pdf.cell(0, 6, f"Cliente: {cliente_nome}", ln=True)
    if cliente_contato:
        pdf.cell(0, 6, f"Contato: {cliente_contato}", ln=True)
    
    pdf.ln(5)
    
    # Cabeçalho da Tabela (Bege levemente mais escuro para destaque: RGB 235, 228, 220)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(235, 228, 220)
    pdf.cell(100, 8, "Descrição do Item / Produto", border=1, fill=True)
    pdf.cell(25, 8, "Qtd", border=1, align="C", fill=True)
    pdf.cell(30, 8, "Vlr. Un. (R$)", border=1, align="R", fill=True)
    pdf.cell(35, 8, "Subtotal (R$)", border=1, align="R", fill=True)
    pdf.ln()
    
    # Itens do Orçamento (Preenchimento transparente para manter a cor da página)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_fill_color(247, 243, 238)
    for item in itens:
        nome_curto = item['nome'][:50] + "..." if len(item['nome']) > 53 else item['nome']
        pdf.cell(100, 7, nome_curto, border=1, fill=True)
        pdf.cell(25, 7, str(item['qtd']), border=1, align="C", fill=True)
        pdf.cell(30, 7, f"{item['preco_unit']:.2f}", border=1, align="R", fill=True)
        pdf.cell(35, 7, f"{item['subtotal']:.2f}", border=1, align="R", fill=True)
        pdf.ln()
        
    # Totalizador
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(155, 8, "VALOR TOTAL ESTIMADO:", border=0, align="R")
    pdf.set_fill_color(235, 228, 220)
    pdf.cell(35, 8, f"R$ {valor_total:.2f}", border=1, align="R", fill=True)
    
    return bytes(pdf.output())

# ==========================================
# BANCO DE DADOS
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            email TEXT,
            cpf_cnpj TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT,
            preco REAL NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            tipo_operacao TEXT,
            data TEXT,
            valor_total REAL,
            desconto REAL,
            valor_final REAL,
            forma_pagamento TEXT,
            status TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO produtos (nome, categoria, preco) VALUES
            ('CHAVEIRO CORDÃO (Poliéster Acetinado 20mm - Colorido Frente e Verso - 11x2cm)', 'Chaveiros / Brindes', 9.17),
            ('CHAVEIRO ABRIDOR (Ferro - Gravação a Laser - 3,8x0,7cm)', 'Chaveiros / Brindes', 4.17)
        ''')
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# SISTEMA DE AUTENTICAÇÃO (LOGIN)
# ==========================================
def checar_login():
    if 'autenticado' not in st.session_state:
        st.session_state['autenticado'] = False

    if not st.session_state['autenticado']:
        st.markdown("<h1 class='main-title'>🎨 CL Artes - Acesso ao Sistema</h1>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("🔑 Digite suas credenciais")
            usuario_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            
            if st.button("Entrar", use_container_width=True):
                if usuario_input == "ADM" and senha_input == "ADM":
                    st.session_state['autenticado'] = True
                    st.session_state['usuario_atual'] = usuario_input
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        return False
    return True

if not checar_login():
    st.stop()

# ==========================================
# BARRA LATERAL
# ==========================================
st.sidebar.title(f"👤 Olá, {st.session_state.get('usuario_atual', 'Usuário')}")
if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state['autenticado'] = False
    st.rerun()

st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Navegação",
    ["🛒 PDV / Caixa", "📄 Gerar Orçamento", "🧮 Precificadora DTF", "👥 Clientes", "📦 Catálogo de Produtos", "📊 Vendas / Histórico"]
)

# ==========================================
# FUNÇÕES DE APOIO
# ==========================================
def get_clientes():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, nome, telefone FROM clientes ORDER BY nome", conn)
    conn.close()
    return df

def get_produtos():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, nome AS 'Nome do Produto', categoria AS 'Categoria', preco AS 'Preço de Venda (R$)' FROM produtos ORDER BY nome", conn)
    conn.close()
    return df

# ==========================================
# 1. MÓDULO: PDV / CAIXA
# ==========================================
if menu == "🛒 PDV / Caixa":
    st.markdown("<h1 class='main-title'>🛒 Frente de Caixa - PDV</h1>", unsafe_allow_html=True)
    
    df_clientes = get_clientes()
    opcoes_clientes = {"Cliente Não Identificado (Balcão)": None}
    for idx, row in df_clientes.iterrows():
        opcoes_clientes[f"{row['nome']} - {row['telefone']}"] = row['id']
        
    cliente_selecionado_str = st.selectbox("Selecione o Cliente:", list(opcoes_clientes.keys()))
    cliente_id = opcoes_clientes[cliente_selecionado_str]
    
    st.markdown("---")
    
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []
        
    col_prod, col_carrinho = st.columns([1, 1])
    
    with col_prod:
        st.subheader("Adicionar Itens")
        df_produtos = get_produtos()
        
        tab1, tab2 = st.tabs(["Produtos Cadastrados", "Item Avulso / Serviço"])
        
        with tab1:
            if not df_produtos.empty:
                prod_nome = st.selectbox("Selecione o Produto:", df_produtos['Nome do Produto'].tolist())
                prod_info = df_produtos[df_produtos['Nome do Produto'] == prod_nome].iloc[0]
                
                if prod_nome in OPCOES_TABELA:
                    tabela_quantidades = OPCOES_TABELA[prod_nome]
                    lista_qtds = list(tabela_quantidades.keys())
                    
                    qtd = st.selectbox("Selecione a Quantidade (Tabela):", lista_qtds, key="qtd_prod_select")
                    preco_unit = tabela_quantidades[qtd]
                    
                    st.markdown("**Preço Unitário Aplicado (Visualização):**")
                    st.subheader(f"R$ {preco_unit:.2f} / un")
                    st.info(f"💡 Total do Item: {qtd} un x R$ {preco_unit:.2f} = **R$ {(qtd * preco_unit):.2f}**")
                else:
                    qtd = st.number_input("Quantidade:", min_value=1, value=1, step=1, key="qtd_prod_input")
                    preco_unit = st.number_input(
                        "Preço Unitário (R$):", 
                        value=float(prod_info['Preço de Venda (R$)']), 
                        format="%.2f", 
                        key="preco_prod_input"
                    )

                if st.button("➕ Adicionar ao Carrinho", type="primary", use_container_width=True):
                    st.session_state.carrinho.append({
                        "nome": prod_nome,
                        "qtd": qtd,
                        "preco_unit": preco_unit,
                        "subtotal": qtd * preco_unit
                    })
                    st.success("Item adicionado ao carrinho!")
                    st.rerun()
            else:
                st.info("Nenhum produto cadastrado no catálogo.")
                
        with tab2:
            nome_avulso = st.text_input("Descrição do Item / Serviço:")
            qtd_avulso = st.number_input("Quantidade:", min_value=1, value=1, key="qtd_avulso")
            preco_avulso = st.number_input("Valor Unitário (R$):", min_value=0.01, value=10.0, step=1.0, key="preco_avulso")
            
            if st.button("➕ Adicionar Item Avulso"):
                if nome_avulso:
                    st.session_state.carrinho.append({
                        "nome": nome_avulso,
                        "qtd": qtd_avulso,
                        "preco_unit": preco_avulso,
                        "subtotal": qtd_avulso * preco_avulso
                    })
                    st.success("Item avulso adicionado!")
                    st.rerun()
                else:
                    st.warning("Preencha a descrição do item.")
                    
    with col_carrinho:
        st.subheader("Resumo da Venda")
        
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            st.dataframe(df_cart[['nome', 'qtd', 'preco_unit', 'subtotal']], use_container_width=True)
            
            total_bruto = sum(item['subtotal'] for item in st.session_state.carrinho)
            
            col_desc, col_pagto = st.columns(2)
            with col_desc:
                desconto = st.number_input("Desconto (R$):", min_value=0.0, max_value=float(total_bruto), value=0.0)
            with col_pagto:
                forma_pagto = st.selectbox("Forma de Pagamento:", ["Pix", "Dinheiro", "Cartão de Crédito", "Cartão de Débito", "Link de Pagamento"])
                
            total_final = total_bruto - desconto
            
            st.markdown(f"### **Total Final: R$ {total_final:.2f}**")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("✅ Finalizar Venda", type="primary", use_container_width=True):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO vendas (cliente_id, tipo_operacao, data, valor_total, desconto, valor_final, forma_pagamento, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (cliente_id, 'PDV', datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total_bruto, desconto, total_final, forma_pagamento, 'Concluída'))
                    conn.commit()
                    conn.close()
                    
                    st.session_state.carrinho = []
                    st.balloons()
                    st.success("Venda registrada com sucesso!")
                    st.rerun()
                    
            with col_b2:
                if st.button("🗑️ Limpar Carrinho", use_container_width=True):
                    st.session_state.carrinho = []
                    st.rerun()
        else:
            st.info("O carrinho está vazio.")

# ==========================================
# 2. MÓDULO: GERAR ORÇAMENTO (PDF)
# ==========================================
elif menu == "📄 Gerar Orçamento":
    st.markdown("<h1 class='main-title'>📄 Gerador de Orçamento em PDF</h1>", unsafe_allow_html=True)
    
    df_clientes = get_clientes()
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if not df_clientes.empty:
            opcoes_cli_orc = {f"{row['nome']} ({row['telefone']})": row for _, row in df_clientes.iterrows()}
            cliente_sel_str = st.selectbox("Selecione o Cliente:", list(opcoes_cli_orc.keys()))
            cliente_info = opcoes_cli_orc[cliente_sel_str]
            cliente_nome = cliente_info['nome']
            cliente_contato = cliente_info['telefone']
            cliente_id = cliente_info['id']
        else:
            st.warning("Nenhum cliente cadastrado. Cadastre um cliente na aba '👥 Clientes'.")
            cliente_nome = st.text_input("Nome do Cliente (Avulso):", value="Cliente Não Cadastrado")
            cliente_contato = ""
            cliente_id = None
            
    st.divider()
    
    if 'itens_orcamento' not in st.session_state:
        st.session_state.itens_orcamento = []
        
    col_item_form, col_item_list = st.columns([1, 1])
    
    with col_item_form:
        st.subheader("Adicionar Itens ao Orçamento")
        df_produtos = get_produtos()
        
        if not df_produtos.empty:
            prod_orc_nome = st.selectbox("Selecione o Produto:", df_produtos['Nome do Produto'].tolist(), key="prod_orc")
            prod_orc_info = df_produtos[df_produtos['Nome do Produto'] == prod_orc_nome].iloc[0]
            
            if prod_orc_nome in OPCOES_TABELA:
                tabela_quantidades = OPCOES_TABELA[prod_orc_nome]
                qtd_orc = st.selectbox("Selecione a Quantidade:", list(tabela_quantidades.keys()), key="qtd_orc_sel")
                preco_orc_unit = tabela_quantidades[qtd_orc]
                st.info(f"Valor Unitário: R$ {preco_orc_unit:.2f} | Subtotal: R$ {(qtd_orc * preco_orc_unit):.2f}")
            else:
                qtd_orc = st.number_input("Quantidade:", min_value=1, value=1, step=1, key="qtd_orc_num")
                preco_orc_unit = st.number_input("Preço Unitário (R$):", value=float(prod_orc_info['Preço de Venda (R$)']), step=0.50, key="preco_orc_num")
                
            if st.button("➕ Incluir no Orçamento", use_container_width=True):
                st.session_state.itens_orcamento.append({
                    "nome": prod_orc_nome,
                    "qtd": qtd_orc,
                    "preco_unit": preco_orc_unit,
                    "subtotal": qtd_orc * preco_orc_unit
                })
                st.success("Item adicionado ao orçamento!")
                st.rerun()

    with col_item_list:
        st.subheader("Resumo dos Itens do Orçamento")
        
        if st.session_state.itens_orcamento:
            df_orc = pd.DataFrame(st.session_state.itens_orcamento)
            st.dataframe(df_orc[['nome', 'qtd', 'preco_unit', 'subtotal']], use_container_width=True)
            
            total_orc = sum(item['subtotal'] for item in st.session_state.itens_orcamento)
            st.markdown(f"### **Total do Orçamento: R$ {total_orc:.2f}**")
            
            pdf_data = gerar_pdf_bytes(cliente_nome, cliente_contato, st.session_state.itens_orcamento, total_orc)
            
            col_b_dl, col_b_salvar, col_b_cls = st.columns(3)
            
            with col_b_dl:
                st.download_button(
                    label="📥 Baixar PDF",
                    data=pdf_data,
                    file_name=f"Orcamento_CL_Artes_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
                
            with col_b_salvar:
                if st.button("💾 Salvar no Histórico", use_container_width=True):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO vendas (cliente_id, tipo_operacao, data, valor_total, desconto, valor_final, forma_pagamento, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (cliente_id, 'Orçamento PDF', datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total_orc, 0.0, total_orc, 'Orçamento', 'Pendente'))
                    conn.commit()
                    conn.close()
                    st.success("Orçamento salvo no histórico com sucesso!")
                    
            with col_b_cls:
                if st.button("🗑️ Limpar", use_container_width=True):
                    st.session_state.itens_orcamento = []
                    st.rerun()
        else:
            st.info("Nenhum item adicionado ao orçamento até o momento.")

# ==========================================
# 3. MÓDULO: PRECIFICADORA DTF
# ==========================================
elif menu == "🧮 Precificadora DTF":
    st.markdown("<h1 class='main-title'>🧮 Calculadora de Orçamento DTF</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Parâmetros do Impresso")
        largura_cm = st.number_input("Largura da Arte (cm):", min_value=1.0, value=10.0, step=0.5)
        altura_cm = st.number_input("Altura da Arte (cm):", min_value=1.0, value=10.0, step=0.5)
        quantidade = st.number_input("Quantidade de Unidades:", min_value=1, value=50, step=1)
        
        st.subheader("Custos de Produção (Folha 1m x 0.40m)")
        custo_metro = st.number_input("Custo do Metro Linear de DTF (R$):", min_value=0.0, value=45.0, step=1.0)
        margem_lucro = st.slider("Margem de Lucro (%):", min_value=10, max_value=300, value=100)
        taxa_extra = st.number_input("Taxas Adicionais / Criação de Arte (R$):", min_value=0.0, value=0.0)

    with col2:
        st.subheader("Cálculo e Resultado")
        
        LARGURA_UTIL_FOLHA = 40.0
        artes_por_largura = math.floor(LARGURA_UTIL_FOLHA / largura_cm)
        if artes_por_largura < 1:
            artes_por_largura = 1
            st.warning("⚠️ A largura da arte excede a largura padrão da folha (40cm).")
            
        linhas_necessarias = math.ceil(quantidade / artes_por_largura)
        comprimento_total_cm = linhas_necessarias * altura_cm
        metros_necessarios = comprimento_total_cm / 100.0
        
        custo_total_dtf = metros_necessarios * custo_metro
        custo_total = custo_total_dtf + taxa_extra
        
        preco_venda_total = custo_total * (1 + (margem_lucro / 100.0))
        preco_unitario = preco_venda_total / quantidade
        
        st.markdown(f"""
        <div class='metric-card'>
            <h4>📊 Resumo do Orçamento:</h4>
            <p><b>Metragem Necessária:</b> {metros_necessarios:.2f} metros lineares</p>
            <p><b>Artes por Fila (Largura):</b> {artes_por_largura} unid.</p>
            <p><b>Custo Total Estimado:</b> R$ {custo_total:.2f}</p>
            <hr>
            <h3><b>Valor Total da Venda: R$ {preco_venda_total:.2f}</b></h3>
            <h4><b>Preço por Unidade: R$ {preco_unitario:.2f}</b></h4>
        </div>
        """, unsafe_allow_html=True)
        
        df_cli = get_clientes()
        cli_dict = {"Cliente Não Registrado": None}
        for idx, row in df_cli.iterrows():
            cli_dict[row['nome']] = row['id']
            
        cli_orc = st.selectbox("Vincular Orçamento ao Cliente:", list(cli_dict.keys()))
        cli_orc_id = cli_dict[cli_orc]
        
        if st.button("💾 Salvar Orçamento no Histórico"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO vendas (cliente_id, tipo_operacao, data, valor_total, desconto, valor_final, forma_pagamento, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (cli_orc_id, 'Orçamento DTF', datetime.now().strftime("%Y-%m-%d %H:%M:%S"), preco_venda_total, 0.0, preco_venda_total, 'Orçamento', 'Pendente'))
            conn.commit()
            conn.close()
            st.success("Orçamento gravado com sucesso no histórico!")

# ==========================================
# 4. MÓDULO: GERENCIAMENTO DE CLIENTES
# ==========================================
elif menu == "👥 Clientes":
    st.markdown("<h1 class='main-title'>👥 Gestão de Clientes</h1>", unsafe_allow_html=True)
    
    tab_cad, tab_list = st.tabs(["➕ Cadastrar Cliente", "📋 Lista de Clientes"])
    
    with tab_cad:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            nome_cli = st.text_input("Nome Completo / Razão Social:")
            telefone_cli = st.text_input("Telefone / WhatsApp:")
        with col_c2:
            email_cli = st.text_input("E-mail:")
            cpf_cnpj_cli = st.text_input("CPF / CNPJ:")
            
        if st.button("Salvar Cliente", type="primary"):
            if nome_cli:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO clientes (nome, telefone, email, cpf_cnpj)
                    VALUES (?, ?, ?, ?)
                ''', (nome_cli, telefone_cli, email_cli, cpf_cnpj_cli))
                conn.commit()
                conn.close()
                st.success(f"Cliente '{nome_cli}' cadastrado com sucesso!")
            else:
                st.warning("O campo Nome é obrigatório.")
                
    with tab_list:
        df_clientes = get_clientes()
        if not df_clientes.empty:
            st.dataframe(df_clientes, use_container_width=True)
        else:
            st.info("Nenhum cliente cadastrado.")

# ==========================================
# 5. MÓDULO: CATÁLOGO DE PRODUTOS
# ==========================================
elif menu == "📦 Catálogo de Produtos":
    st.markdown("<h1 class='main-title'>📦 Catálogo de Produtos & Tabelas de Preço</h1>", unsafe_allow_html=True)
    
    tab_p1, tab_p2, tab_p3, tab_p4 = st.tabs([
        "➕ Novo Produto", 
        "✏️ Editar / Alterar Preço", 
        "📋 Produtos Cadastrados", 
        "🏷️ Tabela de Atacado / Escala"
    ])
    
    # --- CADASTRO DE PRODUTO ---
    with tab_p1:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            nome_prod = st.text_input("Nome do Produto / Item:")
            categoria_prod = st.text_input("Categoria (ex: Chaveiros, Camisetas):")
        with col_p2:
            preco_prod = st.number_input("Preço Base de Venda (R$):", min_value=0.01, value=25.0, step=1.0)
            
        if st.button("Cadastrar Produto", type="primary"):
            if nome_prod:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO produtos (nome, categoria, preco)
                    VALUES (?, ?, ?)
                ''', (nome_prod, categoria_prod, preco_prod))
                conn.commit()
                conn.close()
                st.success(f"Produto '{nome_prod}' cadastrado com sucesso!")
                st.rerun()
            else:
                st.warning("O nome do produto é obrigatório.")
                
    # --- EDIÇÃO / ALTERAÇÃO DE PREÇO ---
    with tab_p2:
        df_prod_edit = get_produtos()
        if not df_prod_edit.empty:
            prod_edit_dict = {f"{row['Nome do Produto']} (R$ {row['Preço de Venda (R$)']:.2f})": row for _, row in df_prod_edit.iterrows()}
            prod_sel_str = st.selectbox("Selecione o Produto para Editar:", list(prod_edit_dict.keys()))
            
            prod_sel = prod_edit_dict[prod_sel_str]
            prod_id = prod_sel['id']
            
            st.divider()
            st.subheader("Editar Informações do Produto")
            
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                novo_nome = st.text_input("Nome do Produto:", value=prod_sel['Nome do Produto'])
                nova_categoria = st.text_input("Categoria:", value=prod_sel['Categoria'])
            with col_e2:
                novo_preco = st.number_input("Preço de Venda (R$):", min_value=0.01, value=float(prod_sel['Preço de Venda (R$)']), step=0.50, format="%.2f")
            
            col_b_save, col_b_del = st.columns([2, 1])
            with col_b_save:
                if st.button("💾 Salvar Alterações", type="primary", use_container_width=True):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE produtos 
                        SET nome = ?, categoria = ?, preco = ? 
                        WHERE id = ?
                    ''', (novo_nome, nova_categoria, novo_preco, prod_id))
                    conn.commit()
                    conn.close()
                    st.success("Produto atualizado com sucesso!")
                    st.rerun()
                    
            with col_b_del:
                if st.button("🗑️ Excluir Produto", use_container_width=True):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM produtos WHERE id = ?', (prod_id,))
                    conn.commit()
                    conn.close()
                    st.warning("Produto excluído do catálogo!")
                    st.rerun()
        else:
            st.info("Nenhum produto cadastrado para edição.")

    # --- LISTA DE PRODUTOS ---
    with tab_p3:
        df_prod = get_produtos()
        if not df_prod.empty:
            st.dataframe(df_prod[['Nome do Produto', 'Categoria', 'Preço de Venda (R$)']], use_container_width=True)
        else:
            st.info("Nenhum produto cadastrado.")

    # --- TABELA DE ATACADO ---
    with tab_p4:
        st.subheader("Tabelas de Desconto Progressivo por Quantidade")
        
        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            st.markdown("### 🔑 CHAVEIRO CORDÃO")
            st.caption("Poliéster Acetinado 20mm - Colorido Frente e Verso - 11x2cm")
            df_cordao = pd.DataFrame([
                {"Qtd Mínima": "30 un", "Preço Un.": "R$ 9,17", "Total": "R$ 275,00"},
                {"Qtd Mínima": "60 un", "Preço Un.": "R$ 8,75", "Total": "R$ 525,00"},
                {"Qtd Mínima": "90 un", "Preço Un.": "R$ 8,33", "Total": "R$ 750,00"}
            ])
            st.table(df_cordao)

        with col_t2:
            st.markdown("### 🔑 CHAVEIRO ABRIDOR")
            st.caption("Ferro - Gravação a Laser - 3,8x0,7cm")
            df_abridor = pd.DataFrame([
                {"Qtd Mínima": "10 un",   "Preço Un.": "R$ 4,17", "Total": "R$ 41,67"},
                {"Qtd Mínima": "20 un",   "Preço Un.": "R$ 3,92", "Total": "R$ 78,33"},
                {"Qtd Mínima": "50 un",   "Preço Un.": "R$ 3,83", "Total": "R$ 191,67"},
                {"Qtd Mínima": "100 un",  "Preço Un.": "R$ 3,75", "Total": "R$ 375,00"},
                {"Qtd Mínima": "250 un",  "Preço Un.": "R$ 3,71", "Total": "R$ 926,67"},
                {"Qtd Mínima": "500 un",  "Preço Un.": "R$ 3,67", "Total": "R$ 1.833,17"},
                {"Qtd Mínima": "1000 un", "Preço Un.": "R$ 3,50", "Total": "R$ 3.499,83"}
            ])
            st.table(df_abridor)

# ==========================================
# 6. MÓDULO: HISTÓRICO DE VENDAS
# ==========================================
elif menu == "📊 Vendas / Histórico":
    st.markdown("<h1 class='main-title'>📊 Histórico de Vendas e Orçamentos</h1>", unsafe_allow_html=True)
    
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT 
            v.id AS 'ID Venda',
            v.data AS 'Data/Hora',
            COALESCE(c.nome, 'Cliente Balcão') AS 'Cliente',
            v.tipo_operacao AS 'Tipo',
            v.forma_pagamento AS 'Pagamento',
            v.valor_final AS 'Valor Final (R$)',
            v.status AS 'Status'
        FROM vendas v
        LEFT JOIN clientes c ON v.cliente_id = c.id
        ORDER BY v.id DESC
    '''
    df_vendas = pd.read_sql_query(query, conn)
    conn.close()
    
    if not df_vendas.empty:
        st.dataframe(df_vendas, use_container_width=True)
    else:
        st.info("Nenhuma venda ou orçamento registrado até o momento.")
