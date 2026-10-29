# Experimentos de viabilidade com agentes

O agente deve ligar comportamento e demanda à capacidade e ao caixa, explicar mecanismos e recomendar testes reais. Nunca tratar contagem de cenários como prova de validade.

## Três dimensões diferentes

| Dimensão | Pergunta | Como tratar |
|---|---|---|
| Réplicas | Quanto muda o resultado por sorteio? | Repetir a configuração com sementes distintas |
| Condições | E se preço, demanda, custos ou capacidade mudarem? | Comparar combinações justificadas |
| Estrutura | E se a influência entre consumidores funcionar de outra maneira? | Comparar regras e redes plausíveis |

Mais agentes não equivalem automaticamente a mais representatividade. A calibração empírica de modelos de difusão é um desafio específico: [Kotthoff e Hamacher, 2022](https://www.jasss.org/25/3/4.html), acessado em 2026-10-29. O [Green Book](https://www.gov.uk/government/publications/the-green-book--2/the-green-book-2026), acessado em 2026-10-29, sustenta análise de alternativas, riscos, sensibilidade e hipóteses; sua finalidade original é avaliação pública, não certificação comercial.

## Preparação na CLI

```bash
python3 .agents/skills/systemic-engineering/scripts/sef.py sim plan \
  --config examples/agent-experiment-plan.json > plano.json
```

Não precisa de projeto e não altera estado, aprova, acessa serviços nem executa experimentos. O JSON contém `base_config` (engine=agents e um cenário), `replicas_per_case` e `factors`. Cada fator tem `parameter`, `values`, `source_ids`, `classification` (hypothesis/estimated/observed) e `rationale`. Classificar como hipótese não constitui autorização para alegar que foi observado. O planejador valida forma e limites; fontes precisam existir e ser avaliadas no preflight e na revisão do projeto.

Fatores aceitos: `scenario.price`, `variable_cost`, `fixed_cost`, `conversion`, `churn`, `capacity`, `acquisition_spend`, `initial_cash`, `market_size`; os prefixos `scenario.` são obrigatórios para todos. Configuração: `config.interaction_strength`, `config.network_topology`, `config.agents`. Não há elasticidade preço-demanda implícita. Combinações dependentes precisam de justificativa ou planos separados: testar preço alto e conversão alta não demonstra que esse preço causa essa conversão.

A saída é um desenho fatorial completo, limitado a 256 combinações, 20 milhões de operações de referência por caso e 100 milhões por plano. Todos os valores devem ser explícitos. Cada caso contém configuração e hash. Extraia `cases[i].config` para um arquivo e use os comandos existentes `sim preflight`, `sim authorize` (method e execution) e `sim run`. Não há execução em lote que contorne revisão, limites ou grants individuais.

O exemplo inclui 81 combinações: três preços × três conversões × três intensidades de influência × três redes, com 100 réplicas por combinação = 8.100 trajetórias **planejadas**, não executadas. Valores e referências de entrada são demonstrativos; precisam ser substituídos por evidências e hipóteses revisadas do projeto.

## Redes implementadas

- `ring`: cada agente consulta seus dois vizinhos em um anel.
- `random`: dois contatos sorteados por agente e período.
- `hybrid` (padrão preservado): vizinho anterior e um contato sorteado.

Contatos aleatórios são sorteados com reposição, podendo incluir o próprio agente; não são redes sociais empíricas. Estados são atualizados simultaneamente a partir do período anterior. Adoção continua usando propensão heterogênea de referência, conversão e influência; saída usa churn. Estas são hipóteses, não consumidores entrevistados. Dinheiro resulta da demanda simulada atendida até a capacidade. Ver limitações financeiras em [simulation-engines.md](simulation-engines.md): não há impostos, estoque, CAPEX ou prazos de pagamento implícitos.

## Rodadas e critérios de parada

1. Definir pergunta, métricas, limites de caixa e condições de rejeição antes de testar.
2. Fazer triagem pequena, adequada aos limites computacionais e com faixas fundamentadas.
3. Aumentar réplicas apenas quando o ruído atrapalhar a comparação. Não há quantidade universal suficiente.
4. Reavaliar candidatos em sementes reservadas, condições adversas e redes alternativas; não escolher e avaliar apenas nos mesmos sorteios.
5. Comparar com observações reais e alternativas simples. Sem dados reais, relatar projeção condicional.
6. Encerrar quando a precisão numérica predefinida for suficiente, o orçamento acabar ou a incerteza dominante exigir pesquisa real. Registrar o motivo.

A aproximação do erro-padrão máximo de uma fração Bernoulli é `0,5/raiz(n)`: com 100 réplicas, até 5 pontos percentuais; com 400, até 2,5. Isso mede somente ruído Monte Carlo sob independência condicional. Não é margem de erro da previsão real, nem corrige busca entre muitas estratégias. Perfis, redes e parâmetros podem continuar errados mesmo com milhões de réplicas.

## Entrega para o empresário

Mostrar faixas de clientes, caixa e resultado por estratégia; demanda não atendida; condições de falta de caixa; custo/capacidade decisivos; limites de viabilidade; estabilidade da recomendação entre redes e hipóteses; fontes e próximo teste real. Frequências entre cenários escolhidos não recebem pesos probabilísticos implícitos. Uma proporção favorável entre 81 casos não é probabilidade de sucesso no mercado.

LLMs/OASIS/MatrAIx podem gerar e investigar hipóteses de comunicação ou comportamento sob seus próprios controles. Respostas sintéticas não calibram preferências reais sem validação independente. Não misturar smokes desses backends com resultados do motor local.

## Acompanhamento integrado no projeto

Cada fator recebe `role`: `decision` (escolha do responsável), `uncertainty` (condição desconhecida) ou `structural` (regra/rede alternativa). O registro de campanha exige pelo menos uma decisão explícita. O comando `sim plan` continua disponível sem projeto; `sim campaign-register PROJETO --config plano.json` valida referências e escopo antes de persistir. `sim campaign-next PROJETO --campaign-id CAM-ID` devolve o próximo caso pendente para o agente conduzir preflight e autorizações. `sim campaign-status` reconcilia as execuções com hashes, sem confiar em arquivos soltos. `sim campaign-analyze` compara resultados disponíveis e registra a cobertura.

A comparação agrupa escolhas humanas e apresenta o pior caixa p10 entre as condições declaradas. Essa é uma regra explícita de triagem robusta; não representa preferência universal nem aprovação. Campanhas incompletas não recebem candidato final e ficam sinalizadas na qualidade do relatório. Não se atribuem probabilidades iguais aos cenários nem se transforma fração de condições favoráveis em chance de sucesso comercial. Retestes devem usar novos planos/sementes: se houver mais de um resultado para o mesmo caso, o sistema exige esclarecer a ambiguidade em vez de escolher automaticamente o resultado favorável.

`finance` e `price_response` opcionais são explicados em [market-feasibility.md](market-feasibility.md). Uma execução pode variar a conversão base por trajetória e as interações por período; isso combina incerteza de entrada com comportamento multiagente, mantendo hipóteses explícitas. Não implica calibração de preferências reais.
