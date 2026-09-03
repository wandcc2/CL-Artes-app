import streamlit as st
import pandas as pd
import sqlite3
import math
from fpdf import FPDF
import base64
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO INICIAL E ESTILO
# ==========================================
st.set_page_config(
    page_title="CL Artes - Gestão & Precificação",
    page_icon="🎨",
    layout="wide"
)

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
# BANCO DE DADOS (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect('sistema_dtf_v2.db')
    cursor = conn.cursor()
    
    # Tabela de Clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            email TEXT,
            cpf_cnpj TEXT
        )
    ''')
    
    # Tabela de Produtos (Catálogo PDV)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT,
            preco REAL NOT NULL,
            estoque INTEGER DEFAULT 0
        )
    ''')
    
    # Tabela de Vendas (PDV e Orçamentos)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            tipo_operacao TEXT, -- 'PDV' ou 'Orçamento DTF'
            data TEXT,
            valor_total REAL,
            desconto REAL,
            valor_final REAL,
            forma_pagamento TEXT,
            status TEXT, -- 'Concluída', 'Pendente'
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# SISTEMA DE AUTENTICAÇÃO (LOGIN)
# ==========================================
def checar_login():
    """Função para validar login e gerenciar a sessão do usuário"""
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
                # Validação das credenciais iniciais
                if usuario_input == "ADM" and senha_input == "ADM":
                    st.session_state['autenticado'] = True
                    st.session_state['usuario_atual'] = usuario_input
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        return False
    return True

# Bloqueia a execução do restante da aplicação se não estiver logado
if not checar_login():
    st.stop()

# ==========================================
# BARRA LATERAL (Navegação + Logout)
# ==========================================
st.sidebar.title(f"👤 Olá, {st.session_state.get('usuario_atual', 'Usuário')}")
if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state['autenticado'] = False
    st.rerun()

st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Navegação",
    ["🛒 PDV / Caixa", "🧮 Precificadora DTF", "👥 Clientes", "📦 Catálogo de Produtos", "📊 Vendas / Histórico"]
)

# ==========================================
# FUNÇÕES DE APOIO
# ==========================================
def get_clientes():
    conn = sqlite3.connect('sistema_dtf_v2.db')
    df = pd.read_sql_query("SELECT id, nome, telefone FROM clientes ORDER BY nome", conn)
    conn.close()
    return df

def get_produtos():
    conn = sqlite3.connect('sistema_dtf_v2.db')
    df = pd.read_sql_query("SELECT * FROM produtos ORDER BY nome", conn)
    conn.close()
    return df

# ==========================================
# 1. MÓDULO: PDV / CAIXA
# ==========================================
if menu == "🛒 PDV / Caixa":
    st.markdown("<h1 class='main-title'>🛒 Frente de Caixa - PDV</h1>", unsafe_allow_html=True)
    
    # Seleção de Cliente
    df_clientes = get_clientes()
    opcoes_clientes = {"Cliente Não Identificado (Balcão)": None}
    for idx, row in df_clientes.iterrows():
        opcoes_clientes[f"{row['nome']} - {row['telefone']}"] = row['id']
        
    cliente_selecionado_str = st.selectbox("Selecione o Cliente:", list(opcoes_clientes.keys()))
    cliente_id = opcoes_clientes[cliente_selecionado_str]
    
    st.markdown("---")
    
    # Carrinho de Compras na Sessão
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []
        
    col_prod, col_carrinho = st.columns([1, 1])
    
    with col_prod:
        st.subheader("Adicionar Itens")
        df_produtos = get_produtos()
        
        tab1, tab2 = st.tabs(["Produtos Cadastrados", "Item Avulso / Serviço"])
        
        with tab1:
            if not df_produtos.empty:
                prod_nome = st.selectbox("Selecione o Produto:", df_produtos['nome'].tolist())
                prod_info = df_produtos[df_produtos['nome'] == prod_nome].iloc[0]
                
                qtd = st.number_input("Quantidade:", min_value=1, value=1, key="qtd_prod")
                preco_unit = st.number_input("Preço Unitário (R$):", value=float(prod_info['preco']), key="preco_prod")
                
                if st.button("➕ Adicionar ao Carrinho"):
                    st.session_state.carrinho.append({
                        "nome": prod_info['nome'],
                        "qtd": qtd,
                        "preco_unit": preco_unit,
                        "subtotal": qtd * preco_unit
                    })
                    st.success("Item adicionado!")
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
                    conn = sqlite3.connect('sistema_dtf_v2.db')
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
# 2. MÓDULO: PRECIFICADORA DTF
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
        
        # Área útil da folha DTF (40cm de largura x 100cm de comprimento)
        LARGURA_UTIL_FOLHA = 40.0
        
        # Quantas artes cabem na largura da folha
        artes_por_largura = math.floor(LARGURA_UTIL_FOLHA / largura_cm)
        if artes_por_largura < 1:
            artes_por_largura = 1
            st.warning("⚠️ A largura da arte excede a largura padrão da folha (40cm).")
            
        # Linhas necessárias para suprir a quantidade
        linhas_necessarias = math.ceil(quantidade / artes_por_largura)
        
        # Comprimento total em metros necessário
        comprimento_total_cm = linhas_necessarias * altura_cm
        metros_necessarios = comprimento_total_cm / 100.0
        
        # Custos
        custo_total_dtf = metros_necessarios * custo_metro
        custo_total = custo_total_dtf + taxa_extra
        
        # Preço final com margem
        preco_venda_total = custo_total * (1 + (margem_lucro / 100.0))
        preco_unitario = preco_venda_total / quantidade
        
        st.markdown(f"""
        <div class='metric-card'>
            <h4>📊 Resumo do Orçamento:</h4>
            <p><b>Metragem Necesária:</b> {metros_necessarios:.2f} metros lineares</p>
            <p><b>Artes por Fila (Largura):</b> {artes_por_largura} unid.</p>
            <p><b>Custo Total Estimado:</b> R$ {custo_total:.2f}</p>
            <hr>
            <h3><b>Valor Total da Venda: R$ {preco_venda_total:.2f}</b></h3>
            <h4><b>Preço por Unidade: R$ {preco_unitario:.2f}</b></h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Seleção de cliente para salvar o orçamento
        df_cli = get_clientes()
        cli_dict = {"Cliente Não Registrado": None}
        for idx, row in df_cli.iterrows():
            cli_dict[row['nome']] = row['id']
            
        cli_orc = st.selectbox("Vincular Orçamento ao Cliente:", list(cli_dict.keys()))
        cli_orc_id = cli_dict[cli_orc]
        
        if st.button("💾 Salvar Orçamento no Histórico"):
            conn = sqlite3.connect('sistema_dtf_v2.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO vendas (cliente_id, tipo_operacao, data, valor_total, desconto, valor_final, forma_pagamento, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (cli_orc_id, 'Orçamento DTF', datetime.now().strftime("%Y-%m-%d %H:%M:%S"), preco_venda_total, 0.0, preco_venda_total, 'Orçamento', 'Pendente'))
            conn.commit()
            conn.close()
            st.success("Orçamento gravado com sucesso no histórico!")

# ==========================================
# 3. MÓDULO: GERENCIAMENTO DE CLIENTES
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
                conn = sqlite3.connect('sistema_dtf_v2.db')
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
# 4. MÓDULO: CATÁLOGO DE PRODUTOS
# ==========================================
elif menu == "📦 Catálogo de Produtos":
    st.markdown("<h1 class='main-title'>📦 Catálogo de Produtos</h1>", unsafe_allow_html=True)
    
    tab_p1, tab_p2 = st.tabs(["➕ Novo Produto", "📋 Produtos Cadastrados"])
    
    with tab_p1:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            nome_prod = st.text_input("Nome do Produto / Item:")
            categoria_prod = st.text_input("Categoria (ex: Camisetas, Canecas, Mídia):")
        with col_p2:
            preco_prod = st.number_input("Preço de Venda (R$):", min_value=0.01, value=25.0, step=1.0)
            estoque_prod = st.number_input("Estoque Inicial:", min_value=0, value=10, step=1)
            
        if st.button("Cadastrar Produto", type="primary"):
            if nome_prod:
                conn = sqlite3.connect('sistema_dtf_v2.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO produtos (nome, categoria, preco, estoque)
                    VALUES (?, ?, ?, ?)
                ''', (nome_prod, categoria_prod, preco_prod, estoque_prod))
                conn.commit()
                conn.close()
                st.success(f"Produto '{nome_prod}' cadastrado com sucesso!")
            else:
                st.warning("O nome do produto é obrigatório.")
                
    with tab_p2:
        df_prod = get_produtos()
        if not df_prod.empty:
            st.dataframe(df_prod, use_container_width=True)
        else:
            st.info("Nenhum produto cadastrado.")

# ==========================================
# 5. MÓDULO: HISTÓRICO DE VENDAS
# ==========================================
elif menu == "📊 Vendas / Histórico":
    st.markdown("<h1 class='main-title'>📊 Histórico de Vendas e Orçamentos</h1>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('sistema_dtf_v2.db')
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
