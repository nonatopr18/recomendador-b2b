from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


COLUNAS = {
    "clientes": {"cliente_id", "nome", "segmento", "porte", "estado"},
    "produtos": {
        "produto_id", "nome_produto", "categoria", "preco", "margem",
        "recorrente", "ativo"
    },
    "compras": {
        "pedido_id", "cliente_id", "produto_id", "data", "quantidade",
        "valor_total"
    },
}


def _validar_colunas(df: pd.DataFrame, esperadas: set[str], nome: str) -> None:
    faltantes = esperadas - set(df.columns)
    if faltantes:
        raise ValueError(f"{nome}.csv não possui: {', '.join(sorted(faltantes))}")


def carregar_dados(pasta: str | Path = "dados"):
    pasta = Path(pasta)
    clientes = pd.read_csv(pasta / "clientes.csv", dtype={"cliente_id": str})
    produtos = pd.read_csv(pasta / "produtos.csv", dtype={"produto_id": str})
    compras = pd.read_csv(
        pasta / "compras.csv",
        dtype={"cliente_id": str, "produto_id": str, "pedido_id": str},
        parse_dates=["data"],
    )

    _validar_colunas(clientes, COLUNAS["clientes"], "clientes")
    _validar_colunas(produtos, COLUNAS["produtos"], "produtos")
    _validar_colunas(compras, COLUNAS["compras"], "compras")

    produtos["ativo"] = produtos["ativo"].astype(str).str.lower().isin(["true", "1", "sim"])
    produtos["recorrente"] = produtos["recorrente"].astype(str).str.lower().isin(["true", "1", "sim"])
    compras = compras.dropna(subset=["cliente_id", "produto_id", "data"])
    return clientes, produtos, compras


@dataclass
class Configuracao:
    peso_coocorrencia: float = 0.75
    peso_segmento: float = 0.25
    dias_bloqueio_recorrente: int = 90
    suporte_minimo: int = 2


class RecomendadorVendaCruzada:
    """Recomendador híbrido: item-item + popularidade no segmento B2B."""

    def __init__(self, configuracao: Configuracao | None = None):
        self.config = configuracao or Configuracao()

    def fit(self, clientes: pd.DataFrame, produtos: pd.DataFrame, compras: pd.DataFrame):
        self.clientes = clientes.copy()
        self.produtos = produtos.copy()
        self.compras = compras.copy()

        # Presença do produto por cliente evita que grandes compradores dominem.
        cesta = (
            compras.assign(comprou=1)
            .pivot_table(
                index="cliente_id", columns="produto_id", values="comprou",
                aggfunc="max", fill_value=0
            )
            .astype(float)
        )
        self.cesta = cesta

        cooc = cesta.T.dot(cesta)
        suporte = np.diag(cooc).astype(float)
        denominador = np.sqrt(np.outer(suporte, suporte))
        similaridade = np.divide(
            cooc.to_numpy(dtype=float),
            denominador,
            out=np.zeros_like(cooc.to_numpy(dtype=float)),
            where=denominador > 0,
        )
        np.fill_diagonal(similaridade, 0)
        similaridade[:, suporte < self.config.suporte_minimo] = 0
        self.similaridade = pd.DataFrame(
            similaridade, index=cooc.index, columns=cooc.columns
        )

        compras_segmento = compras.merge(
            clientes[["cliente_id", "segmento"]], on="cliente_id", how="left"
        )
        popularidade = (
            compras_segmento.groupby(["segmento", "produto_id"])["cliente_id"]
            .nunique()
            .rename("clientes_compradores")
            .reset_index()
        )
        popularidade["score_segmento"] = popularidade.groupby("segmento")[
            "clientes_compradores"
        ].transform(lambda x: x / x.max() if x.max() else 0)
        self.popularidade_segmento = popularidade
        return self

    def recomendar(self, cliente_id: str, quantidade: int = 5) -> pd.DataFrame:
        cliente_id = str(cliente_id)
        perfil = self.clientes[self.clientes["cliente_id"] == cliente_id]
        if perfil.empty:
            raise ValueError(f"Cliente {cliente_id} não encontrado.")

        segmento = perfil.iloc[0]["segmento"]
        historico = self.compras[self.compras["cliente_id"] == cliente_id].copy()
        comprados = set(historico["produto_id"])

        scores_item = pd.Series(0.0, index=self.similaridade.columns)
        produto_origem = pd.Series("", index=self.similaridade.columns, dtype=object)

        if comprados:
            sementes = [p for p in comprados if p in self.similaridade.index]
            if sementes:
                matriz = self.similaridade.loc[sementes]
                scores_item = matriz.sum(axis=0)
                produto_origem = matriz.idxmax(axis=0)
                if scores_item.max() > 0:
                    scores_item = scores_item / scores_item.max()

        pop = self.popularidade_segmento.query("segmento == @segmento").set_index("produto_id")
        score_segmento = pop["score_segmento"].reindex(scores_item.index).fillna(0)

        resultado = pd.DataFrame({
            "produto_id": scores_item.index,
            "score_coocorrencia": scores_item.values,
            "score_segmento": score_segmento.values,
            "produto_origem": produto_origem.values,
        })
        resultado["score"] = 100 * (
            self.config.peso_coocorrencia * resultado["score_coocorrencia"]
            + self.config.peso_segmento * resultado["score_segmento"]
        )
        resultado = resultado.merge(self.produtos, on="produto_id", how="left")
        resultado = resultado[resultado["ativo"]].copy()

        # Itens não recorrentes já adquiridos não são oferecidos novamente.
        nao_recorrentes = set(
            self.produtos.loc[~self.produtos["recorrente"], "produto_id"]
        )
        bloqueados = comprados & nao_recorrentes

        # Itens recorrentes são liberados somente após a janela configurada.
        limite = pd.Timestamp.today().normalize() - pd.Timedelta(
            days=self.config.dias_bloqueio_recorrente
        )
        recentes = set(historico.loc[historico["data"] >= limite, "produto_id"])
        bloqueados |= recentes
        resultado = resultado[~resultado["produto_id"].isin(bloqueados)]

        nomes = self.produtos.set_index("produto_id")["nome_produto"].to_dict()
        resultado["motivo"] = resultado.apply(
            lambda r: (
                f"Comprado junto com {nomes.get(r['produto_origem'], 'itens do histórico')}"
                if r["score_coocorrencia"] > 0
                else f"Popular entre empresas do segmento {segmento}"
            ),
            axis=1,
        )
        resultado["score"] = resultado["score"].round(1)
        return (
            resultado.sort_values(["score", "margem"], ascending=[False, False])
            .head(quantidade)
            [["produto_id", "nome_produto", "categoria", "preco", "margem", "score", "motivo"]]
            .reset_index(drop=True)
        )

