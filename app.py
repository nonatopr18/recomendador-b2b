from pathlib import Path

import streamlit as st

from recomendador import Configuracao, RecomendadorVendaCruzada, carregar_dados


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

