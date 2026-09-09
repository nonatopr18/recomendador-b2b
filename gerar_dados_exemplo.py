from pathlib import Path

import numpy as np
import pandas as pd


PASTA = Path(__file__).resolve().parent / "dados"
PASTA.mkdir(exist_ok=True)
rng = np.random.default_rng(42)

segmentos = ["Varejo", "Restaurantes", "Saúde", "Indústria", "Serviços"]
portes = ["Pequena", "Média", "Grande"]
estados = ["CE", "RN", "PE", "PB"]

clientes = pd.DataFrame([
    {
        "cliente_id": f"C{i:03d}",
        "nome": f"Empresa {i:03d}",
        "segmento": segmentos[(i - 1) % len(segmentos)],
        "porte": portes[(i - 1) % len(portes)],
        "estado": estados[(i - 1) % len(estados)],
    }
    for i in range(1, 81)
])

catalogo = [
    ("P001", "ERP Essencial", "Software", 499.0, 0.55, True),
    ("P002", "CRM Vendas", "Software", 349.0, 0.62, True),
    ("P003", "Emissor Fiscal", "Software", 179.0, 0.58, True),
    ("P004", "Gestão de Estoque", "Software", 289.0, 0.60, True),
    ("P005", "Analytics Pro", "Software", 429.0, 0.68, True),
    ("P006", "Backup Corporativo", "Infraestrutura", 239.0, 0.57, True),
    ("P007", "Firewall Gerenciado", "Segurança", 599.0, 0.48, True),
    ("P008", "Antivírus Empresarial", "Segurança", 149.0, 0.51, True),
    ("P009", "Suporte Premium", "Serviços", 399.0, 0.70, True),
    ("P010", "Treinamento da Equipe", "Serviços", 1800.0, 0.45, False),
    ("P011", "Leitor de Código de Barras", "Equipamentos", 890.0, 0.28, False),
    ("P012", "Impressora Térmica", "Equipamentos", 1250.0, 0.25, False),
    ("P013", "Gateway de Pagamentos", "Pagamentos", 299.0, 0.52, True),
    ("P014", "Link de Internet Backup", "Infraestrutura", 459.0, 0.38, True),
    ("P015", "Assinatura Eletrônica", "Produtividade", 199.0, 0.64, True),
]
produtos = pd.DataFrame(catalogo, columns=[
    "produto_id", "nome_produto", "categoria", "preco", "margem", "recorrente"
])
produtos["ativo"] = True

preferencias = {
    "Varejo": ["P001", "P003", "P004", "P011", "P012", "P013"],
    "Restaurantes": ["P001", "P003", "P004", "P012", "P013"],
    "Saúde": ["P001", "P006", "P007", "P008", "P015"],
    "Indústria": ["P001", "P004", "P005", "P006", "P007", "P014"],
    "Serviços": ["P001", "P002", "P005", "P006", "P009", "P015"],
}

linhas = []
pedido = 1
hoje = pd.Timestamp.today().normalize()
for cliente in clientes.itertuples():
    preferidos = preferencias[cliente.segmento]
    escolhidos = list(rng.choice(preferidos, size=rng.integers(2, 5), replace=False))
    if rng.random() < 0.45:
        escolhidos.append("P009")
    for produto_id in dict.fromkeys(escolhidos):
        preco = float(produtos.loc[produtos["produto_id"] == produto_id, "preco"].iloc[0])
        quantidade = int(rng.integers(1, 5))
        linhas.append({
            "pedido_id": f"PED{pedido:05d}",
            "cliente_id": cliente.cliente_id,
            "produto_id": produto_id,
            "data": (hoje - pd.Timedelta(days=int(rng.integers(20, 500)))).date(),
            "quantidade": quantidade,
            "valor_total": round(preco * quantidade, 2),
        })
        pedido += 1

pd.DataFrame(linhas).to_csv(PASTA / "compras.csv", index=False, encoding="utf-8-sig")
clientes.to_csv(PASTA / "clientes.csv", index=False, encoding="utf-8-sig")
produtos.to_csv(PASTA / "produtos.csv", index=False, encoding="utf-8-sig")
print(f"Dados criados em {PASTA}")

