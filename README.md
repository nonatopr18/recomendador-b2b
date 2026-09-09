# Sistema de recomendação B2B para venda cruzada

Protótipo híbrido que combina afinidade entre produtos comprados pelos mesmos
clientes e popularidade dentro do segmento empresarial.

## Executar

```powershell
python -m venv ven
.\ven\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python gerar_dados_exemplo.py
python -m streamlit run app.py
```

## Substituir pelos dados reais

Coloque na pasta `dados/` três arquivos CSV:

- `clientes.csv`: cliente_id, nome, segmento, porte, estado
- `produtos.csv`: produto_id, nome_produto, categoria, preco, margem, recorrente, ativo
- `compras.csv`: pedido_id, cliente_id, produto_id, data, quantidade, valor_total

Os identificadores devem ser consistentes entre os três arquivos. As colunas
`recorrente` e `ativo` aceitam `True/False`, `1/0` ou `sim/não`.

## Lógica

- 75% do score: similaridade por coocorrência entre produtos.
- 25% do score: adoção do produto no segmento do cliente.
- Produtos não recorrentes já comprados são bloqueados.
- Produtos recorrentes comprados dentro da janela configurada são bloqueados.
- Produtos inativos nunca são recomendados.

O protótipo não substitui regras comerciais de estoque, contrato, preço,
território, crédito ou elegibilidade. Essas regras devem ser adicionadas antes
do uso em produção.
