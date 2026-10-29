# Viabilidade e mercado: protocolo de aplicação

Use para avaliar lançamento, expansão, preço, capacidade ou investimento. O agente coordena pesquisa, arquivos e CLI; o responsável decide objetivos, perdas aceitáveis e aprovações. O produto é uma recomendação condicional com plano de teste, não um formulário preenchido.

## Pergunta, comparação e critérios

No Intake, explicite o que será decidido, para quem, em qual região, horizonte, moeda e unidade. Pergunte o que tornaria o projeto inviável, qual perda de caixa é tolerável e o que precisa ser observado para avançar. Em VFT, confirme objetivos, prioridades e critérios não compensáveis com os stakeholders. Em SSM, confronte as visões de compradores, operação, fornecedores e financiadores; registre diferenças antes de estabilizar a fronteira. Reconcilie mudanças de escopo e premissas.

Compare a proposta com a continuidade da situação atual, um piloto limitado e alternativas reais quando existirem. Objetivos humanos não são inferidos das preferências de agentes sintéticos. Use STPA para controle e consequências inaceitáveis, sem tratá-la como análise financeira nem substituir especialistas.

## Evidências antes dos parâmetros

Organize demanda, concorrentes/substitutos, preços efetivos, alcance de canais, capacidade, custos, prazos de caixa e riscos. Registre trechos, URLs, datas, população, local e independência. Não inferir vendas, CAC, conversão ou verba de anúncios apenas observando publicidade. Dados privados do responsável podem sustentar contas internas, identificados como declarações/registros internos; não convertê-los em fonte externa. Se faltar evidência, registre hipótese, faixa, justificativa e pesquisa necessária.

Documentação de método não sustenta preços ou demanda de um caso. Pesquise referências da atividade e região antes de preencher entradas. Diferencie variabilidade entre pessoas, mudanças ao longo do tempo e desconhecimento de parâmetros. Não combinar variáveis relacionadas como se fossem independentes sem justificar.

## Escolha de mecanismos

| Questão | Caminho |
|---|---|
| Viabilidade e caixa | Modelo operacional + `finance` opcional + cenários/Monte Carlo |
| Adoção, perfis e influência | `agents`, redes alternativas e réplicas; calibrar antes de alegar previsão de mercado |
| Preferência por preço/atributos | Experimento de escolha com compradores reais; não é substituído por votação de LLMs |
| Crescimento agregado por divulgação/indicação | Considerar modelo de difusão como Bass, ajustado a dados; implementação de referência disponível no PyMC-Marketing, não incorporada automaticamente à CLI |
| Gargalos e atrasos | `dynamics` e mecanismos explícitos; o motor de referência não contém toda realimentação operacional possível |
| Comunicação/personas | OASIS/MatrAIx opcionais, com infraestrutura e autorização; suas respostas continuam sintéticas |
| Previsão/otimização aprendida | Primeiro dados separados, referência simples e erro; ML/BDH não acrescentam validade apenas por serem mais complexos |

Referências externas, acessadas em 2026-10-29:
- [HM Treasury — Green Book](https://www.gov.uk/government/publications/the-green-book--2/the-green-book-2026): comparação de opções, riscos, desconto, sensibilidade e avaliação; contexto original público, adaptar a negócio privado.
- [Kotthoff e Hamacher, 2022](https://www.jasss.org/25/3/4.html): calibração de agentes de difusão com dados empíricos; não demonstra validade das regras locais deste framework.
- [Sawtooth — Choice Simulator](https://info.sawtoothsoftware.com/help/discover/analysis/cbc/market-simulator): transformar pesquisa de escolha em cenários; preferência não equivale automaticamente a participação real.
- [PyMC-Marketing — Bass](https://www.pymc-marketing.io/en/latest/api/generated/pymc_marketing.bass.model.create_bass_model.html): adoção por influência externa e imitação; não é evidência de adoção de uma nova empresa.

## Financeiro explícito

O bloco `finance` pertence a cada cenário e é opcional. Sem ele, permanece o caixa operacional simplificado anterior. Com ele, todos os campos abaixo são obrigatórios:

```json
{
  "initial_investment": 1000,
  "discount_rate_per_period": 0.01,
  "revenue_tax_rate": 0.05,
  "collection_lag": 1,
  "operating_payment_lag": 0,
  "capex": [{"tick": 3, "amount": 300}],
  "source_ids": ["SRC-PREMISSAS"],
  "limitations": "Exemplo hipotético. Validar regime fiscal e condições reais."
}
```

Valores são ilustrativos. Taxa de desconto pertence ao período do cenário: mês, trimestre e ano não são intercambiáveis. Definir preços reais/nominais e desconto consistente; o código não converte inflação. `revenue_tax_rate` é dedução proporcional sobre faturamento, paga no mesmo período, sem enquadramento tributário automático. Outras despesas operacionais são pagas após o mesmo `operating_payment_lag`; recebimentos chegam após `collection_lag`. Não existe saldo inicial a receber/pagar implícito. Investimento inicial sai no período zero; CAPEX sai nos períodos declarados. Capital inicial é saldo de caixa disponível, não receita nem benefício do investimento.

Indicadores: VPL = menos investimento inicial + fluxos líquidos descontados; caixa mínimo; capital adicional para cobrir saldo negativo; valores a receber/pagar ao final; primeiro período de recuperação não descontada do investimento; unidades necessárias para cobrir custos fixos e aquisição na margem base. Esta última conta não incorpora choques, CAPEX ou retorno de investimento, e não é viabilidade completa. Recuperação em um período não garante caixa positivo depois. Frequências são condicionais às réplicas; intervalos Wilson no resultado medem apenas erro Monte Carlo.

Não há estoque, inadimplência, financiamento, depreciação, múltiplos regimes fiscais, valor terminal ou liquidação automática de obrigações no fim. Se isso for material, estenda o mecanismo e revise antes de recomendar. VPL de horizonte truncado não é avaliação integral de empresa; exibir saldos pendentes e horizonte. O framework não atribui uma taxa de desconto universal nem emite parecer contábil.

## Resposta a preço e incerteza

Sem `price_response`, preço não modifica conversão. Se essa relação for necessária, o cenário pode declarar:

```json
{"price_response": {"reference_price": 120, "elasticity": -0.8, "source_ids": ["SRC-PREMISSAS"], "classification": "hypothesis"}}
```

A conversão efetiva é a taxa base vezes `(preço/preço_referência)^elasticidade`, limitada a [0,1], antes da influência social. Preço positivo obrigatório; choques também precisam mantê-lo positivo. É uma hipótese de resposta da conversão, não elasticidade de toda a receita nem estimativa causal aprendida. Inicialmente não se combina com o modelo regional. O campo `uncertainty` sorteia a conversão base por trajetória também em `agents`; contatos e decisões individuais acrescentam variação dentro da trajetória. A distribuição continua explícita e hipotética, sem calibração automática.

## Campanhas e entrega

Siga [agent-experiments.md](agent-experiments.md). Separe fatores de decisão, incerteza e estrutura. `campaign-register` valida os casos e persiste o plano; `campaign-next` informa a próxima configuração. O agente prepara o arquivo, apresenta escopo e preflight, obtém as duas autorizações e executa. Repete apenas quando houver autoridade correspondente. `campaign-status` reconcilia execuções; `campaign-analyze` compara a cobertura disponível, sem probabilidades implícitas entre cenários. Há limite computacional, integridade e rejeição de resultados ambíguos; não há bypass de autorização em lote.

A triagem usa o maior caixa p10 no pior dos casos declarados. Explique a métrica, considere os objetivos VFT/MCDA e condições não compensáveis; o candidato não é decisão automática. Verifique estabilidade em redes, hipóteses e sementes reservadas. Estresse não é dado de mercado. Não usar apenas as condições escolhidas para otimizar como demonstração de previsão fora do ajuste.

No relatório/dashboard: trajetória de clientes e caixa; faixas de resultados; investimento e capital adicional; atrasos de recebimento; capacidade não atendida; condições de falta de caixa; comparação de estratégias; fontes; limitações; regra de reversão; plano de ação com dono, prazo e teste real. Documentos seguem a biblioteca generalista. Mapas usam apenas geografia e valores fornecidos; não extrapolar rede de agentes para expansão territorial sem modelo regional explícito.

Separe três alegações: implementação executou; modelo reproduziu observações independentes; estratégia teve resultado observado. O primeiro nível não implica os demais. ML treinado em simulações pode aproximar o simulador, desde que testado em condições reservadas; não valida mercado. Treinar BDH novamente só é justificado por pergunta e dados adequados, com referência simples e possibilidade explícita de resultado negativo.
