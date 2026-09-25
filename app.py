from pathlib import Path

import streamlit as st
import unicodedata

from recomendador import Configuracao, RecomendadorVendaCruzada, carregar_dados
#### Gerar Senha
# ============================================================
# CONFIGURAÇÃO ÚNICA DO STREAMLIT
# ============================================================
st.set_page_config(
    page_title="Classificação de Risco COVID",
    page_icon="🩺",
    layout="wide"
)
# ============================================================
# LOGIN
# ============================================================
def carregar_usuarios():

    try:
        return st.secrets["usuarios"]

    except Exception:
        return None
def normalizar_usuario(texto):
    """Normaliza o usuário para aceitar João, joao, JOAO etc."""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")

def autenticar(usuario, senha):

    usuarios = carregar_usuarios()

    if usuarios is None:
        return False, "Usuários ainda não configurados no Streamlit Secrets."

    usuario_digitado = normalizar_usuario(usuario)
    usuario_encontrado = None

    # Procura o usuário sem diferenciar maiúsculas/minúsculas
    # e sem diferenciar acentos.
    for chave in usuarios:
        if normalizar_usuario(chave) == usuario_digitado:
            usuario_encontrado = chave
            break

    if usuario_encontrado is None:
        return False, "Usuário ou senha inválidos."

    try:
        senha_correta = str(usuarios[usuario_encontrado]["senha"])
    except Exception:
        return False, "Configuração de senha inválida no Streamlit Secrets."

    if hmac.compare_digest(str(senha), senha_correta):

        nome = str(
            usuarios[usuario_encontrado].get(
                "nome",
                usuario_encontrado
            )
        )

        return True, nome

    return False, "Usuário ou senha inválidos."
# ============================================================
# CONTROLE DA SESSÃO
# ============================================================

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False


# ============================================================
# TELA DE LOGIN
# ============================================================

if not st.session_state.autenticado:

    st.title("🔐 Acesso ao sistema")

    st.write(
        "Digite seu usuário e sua senha para continuar."
    )

    usuario = st.text_input(
        "Usuário",
        placeholder="Digite seu usuário"
    )

    senha = st.text_input(
        "Senha",
        type="password",
        placeholder="Digite sua senha"
    )

    if st.button(
        "Entrar",
        use_container_width=True,
        type="primary"
    ):

        if not usuario or not senha:

            st.warning(
                "Informe o usuário e a senha."
            )

        else:

            sucesso, resultado = autenticar(
                usuario,
                senha
            )

            if sucesso:

                st.session_state.autenticado = True
                st.session_state.usuario = usuario
                st.session_state.nome_usuario = resultado

                st.rerun()

            else:

                st.error(resultado)

    # Impede que o restante do aplicativo apareça
    st.stop()


# ============================================================
# USUÁRIO LOGADO
# ============================================================

nome_usuario = st.session_state.get(
    "nome_usuario",
    st.session_state.get("usuario", "")
)


# ============================================================
# BOTÃO SAIR
# ============================================================

with st.sidebar:

    st.success(
        f"👤 Usuário: {nome_usuario}"
    )

    if st.button(
        "🚪 Sair",
        use_container_width=True
    ):

        st.session_state.autenticado = False

        st.session_state.pop(
            "usuario",
            None
        )

        st.session_state.pop(
            "nome_usuario",
            None
        )

        st.rerun()
### Senha Gerada

BASE = Path(__file__).resolve().parent

st.set_page_config(page_title="Recomendador B2B", layout="wide")
st.title(" Recomendador B2B de venda cruzada")
st.caption("Sugestões baseadas em compras conjuntas e comportamento do segmento do cliente.")


@st.cache_resource
def carregar_modelo(dias_bloqueio: int, suporte_minimo: int):
    clientes, produtos, compras = carregar_dados(BASE / "dados")
    modelo = RecomendadorVendaCruzada(
        Configuracao(
            dias_bloqueio_recorrente=dias_bloqueio,
            suporte_minimo=suporte_minimo,
        )
    ).fit(clientes, produtos, compras)
    return clientes, produtos, compras, modelo


with st.sidebar:
    st.header("Configurações")
    quantidade = st.slider("Quantidade de recomendações", 1, 10, 5)
    dias_bloqueio = st.slider("Bloquear recompra por quantos dias", 0, 365, 90, 15)
    suporte_minimo = st.slider("Mínimo de clientes por produto", 1, 10, 2)

try:
    clientes, produtos, compras, modelo = carregar_modelo(dias_bloqueio, suporte_minimo)
except Exception as erro:
    st.error(f"Não foi possível carregar os dados: {erro}")
    st.stop()

opcoes = clientes.assign(rotulo=clientes["cliente_id"] + " — " + clientes["nome"])
rotulo = st.selectbox("Selecione a empresa", opcoes["rotulo"])
cliente_id = rotulo.split(" — ", 1)[0]
perfil = clientes[clientes["cliente_id"] == cliente_id].iloc[0]

c1, c2, c3 = st.columns(3)
c1.metric("Segmento", perfil["segmento"])
c2.metric("Porte", perfil["porte"])
c3.metric("Estado", perfil["estado"])

historico = (
    compras[compras["cliente_id"] == cliente_id]
    .merge(produtos[["produto_id", "nome_produto", "categoria"]], on="produto_id")
    .sort_values("data", ascending=False)
)

st.subheader("Produtos recomendados")
recomendacoes = modelo.recomendar(cliente_id, quantidade)

if recomendacoes.empty:
    st.info("Não há produtos elegíveis com os filtros atuais.")
else:
    exibicao = recomendacoes.copy()
    exibicao["preco"] = exibicao["preco"].map(lambda x: f"R$ {x:,.2f}")
    exibicao["margem"] = exibicao["margem"].map(lambda x: f"{100*x:.1f}%")
    exibicao["score"] = exibicao["score"].map(lambda x: f"{x:.1f}")
    st.dataframe(exibicao, use_container_width=True, hide_index=True)
    st.bar_chart(recomendacoes.set_index("nome_produto")["score"])
    st.download_button(
        "Baixar recomendações",
        recomendacoes.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"recomendacoes_{cliente_id}.csv",
        mime="text/csv",
    )

with st.expander("Ver histórico de compras"):
    st.dataframe(
        historico[["data", "pedido_id", "nome_produto", "categoria", "quantidade", "valor_total"]],
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.caption(
    "O score prioriza afinidade entre produtos (75%) e popularidade no segmento (25%). "
    "Antes de uso comercial, valide regras de estoque, contratos, preço e elegibilidade."
)

