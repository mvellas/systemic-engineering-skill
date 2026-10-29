# Motores e fronteiras de interpretação

## Core local

Todos aceitam seed, timeout, escala e classificação; parâmetros e fontes ficam no manifesto. `sim preflight` limita trabalho de referência a 20 milhões de operações estimadas por chamada, não a 20 milhões de pessoas. Memória é estimativa estrutural e não certificação de escala. Resultado acima do timeout não é aceito. Parâmetros não finitos são rejeitados.

### Monte Carlo, agentes e estoques/fluxos

`engine`: `monte-carlo`, `agents` ou `dynamics`. Configuração mínima no exemplo completo. Cada cenário declara preço, custo variável, fixo, caixa inicial, mercado elegível, conversão por período, churn, capacidade, clientes iniciais, gasto de aquisição, unidade, moeda, período e fontes. Sem entradas, o motor recusa gerar números.

No modelo de referência, um cliente ativo gera no máximo uma unidade por período, limitada pela capacidade; aquisição usa o mercado ainda não ativo. Caixa inicial + entradas − saídas = caixa final. Recebimento e desembolso são no mesmo período. O bloco opcional `finance` acrescenta investimento inicial, CAPEX, taxa proporcional explícita sobre receita e defasagens de recebimento/pagamento; contratos e limites em [market-feasibility.md](market-feasibility.md). Sem esse bloco, não há contabilidade fiscal/tributária, estoque, CAPEX, inadimplência ou parcelamento implícitos. Para decisões que dependam desses mecanismos, estender o modelo antes de recomendar; não aplicar a fórmula indiscriminadamente a qualquer negócio.

Monte Carlo amostra conversão segundo distribuição normal truncada em [0,1], com desvio declarado; a forma é uma hipótese de modelo, não algo aprendido da população. Trajetórias interrompidas por caixa são resumidas separadamente; a série média mostra a quantidade de réplicas presentes. Fração que supera `success.metric/threshold` é frequência condicional nas réplicas, nunca probabilidade calibrada de sucesso comercial.

Agentes são unidades ponderadas com propensão heterogênea. `network_topology` seleciona contatos: hybrid (vizinho anterior + contato sorteado), ring (dois vizinhos) ou random (dois contatos sorteados). `uncertainty` pode variar conversão base por trajetória; `price_response` é opcional e exige premissas explícitas. O estado anterior influencia a adoção; snapshots de até 80 agentes/contatos sustentam a rede visível. Essa representação é deliberadamente simples, sem preferência política inferida ou promessa de representatividade. Dinâmica usa estoques/fluxos determinísticos de aquisição/saída. Descrever hipóteses com ODD antes de ampliar o modelo.

Choques declarados podem alterar preço, custo variável ou conversão, com início, duração, multiplicador e fontes. Sensibilidade varia uma entrada de cada vez na trajetória determinística; não é Sobol nem inferência causal. Preço mais alto com conversão constante aumenta receita por construção: teste elasticidade explicitamente antes de defender aumento de preço.

### Recorte regional opcional

Cenários Monte Carlo/estoques podem declarar `regions: [{id, market_size, initial_customers, conversion, source_ids}]`. Mercados e clientes iniciais regionais precisam somar o total. Cada região evolui seu estoque de clientes com sua conversão e o churn declarado; o choque proporcional de conversão afeta as taxas regionais. Totais e médias regionais usam as mesmas réplicas. Receita e capacidade continuam agregadas: o modelo não inventa logística ou caixa por região. O ABM deste corte não atribui características regionais a indivíduos e exige cenário sem `regions`.

Forneça geometrias em `geography.features`, identificação regional, métrica, unidade, fontes e data-base. O mapa pode ler `regional_timeseries` da execução, mantendo escala fixa entre períodos; regiões não modeladas ficam sem valor, não com zero. No exemplo brasileiro, somente limites territoriais vêm do IBGE; as taxas/mercados SP e DF são hipóteses didáticas explícitas. Isso não demonstra expansão observada nem preferência regional.

### Propagação de falhas

`engine: failure`; `nodes: [{id, failure_probability, recovery_probability}]`; `edges: [{from, to, probability}]`. A propagação usa o estado do período anterior e as probabilidades declaradas. Exibir perdas, contingências e dependências; não substituir STPA por um grafo de falhas. Uma fonte metodológica não torna as taxas empíricas.

### MCMC

`engine: mcmc`; observações `{successes, trials, source_ids}`, prior Beta (`prior_alpha`, `prior_beta`), `chains` 2–8, `trials` passos por cadeia, `warmup`, `proposal_sd`. Metropolis-Hastings gera posterior binomial; a média analítica Beta permite verificar o sampler. Guarda cadeias, aceitação, split R-hat simples e ESS por sequência positiva aproximada. Diagnóstico insuficiente impede tratar a saída como confiável; mesmo um diagnóstico preliminar favorável não prova boa amostragem de clientes.

Não usa HMC/NUTS nem afirma equivalência aos diagnósticos rank-normalizados do Stan. Para modelos hierárquicos ou decisões relevantes, usar ferramenta estatística validada, análise de amostragem, verificação preditiva e revisão especializada. Mais amostras sintéticas não corrigem viés dos dados de entrada.

## Aprendizado e otimização

`engine: ml` exige NumPy, arquivo JSON `dataset`, lista `features`, `training_steps`, `hidden_units`, `learning_rate`. Dataset: `classification` observed/synthetic, `source_ids`, `rows: [{id, date, features: {...}, target}]`. IDs únicos, ordem temporal e períodos separados; mínimo operacional de 20 linhas de treino e cinco de teste, em um total de pelo menos 30 registros. Isso é limite de software, não comprovação de suficiência estatística.

Uma rede pequena tanh é treinada por backpropagation, com normalização aprendida apenas no treino e referência de previsão pela média. Resultado informa MAE/RMSE em holdout, erro da referência e se houve melhora. O holdout não serve para ajustar hiperparâmetros e repetir até “dar certo”; se necessário, acrescente validação temporal aninhada. Correlação preditiva não demonstra efeito causal.

`optimize: {direction: maximize|minimize, start: {feature: valor}, bounds: {feature: [mínimo,máximo]}}` faz busca por gradiente do substituto, dentro da faixa vista no treino. O candidato não é um ótimo do mercado: confrontar com restrições, simulação independente e experimento de campo. Sem superar a referência, não o usar como recomendação.

`engine: bdh` exige PyTorch, fonte oficial local (`bdh_source`), SHA256 (`bdh_source_sha256`) e confirmação de licença. O adapter experimental codifica registros numéricos em uma sequência curta de bytes e aprende 2–8 classes de resultado definidas pelo responsável. Treina de fato com backpropagation, informa acurácia em teste e a referência da classe majoritária. Os scores softmax não são calibrados. Não há checkpoint pré-treinado de “sucesso de negócios”.

Em PyTorch anterior à API `nn.Buffer`, o adapter traduz apenas a atribuição do buffer de frequências para `register_buffer`, preservando a expressão numérica, e registra a compatibilidade no resultado. A fonte oficial original continua identificada por hash. A adaptação precisa ser testada no executor; não afirmar portabilidade de aceleração/GPU sem teste. Otimização contínua de variáveis pertence ao substituto ML, não a inferência causal obtida do BDH.

## OASIS e MatrAIx opcionais

Runtimes ficam separados do core. `sim capabilities` descobre caminhos candidatos existentes; a configuração escolhe `python_executable` absoluto. Não há download, instalação, chave ou uso de API implícitos.

- OASIS: API real `oasis.make`, `AgentGraph`, `SocialAgent`, `ManualAction` e `LLMAction`, com CAMEL `ModelFactory`. `profile_path` e número de perfis devem coincidir com `agents`; `initial_post` define o assunto. O adapter inicial limita LLM comportamental a endpoint vLLM local loopback e custo externo zero. Não suporta execução paga sem medição rígida de custo; recusa esse caso, em vez de fingir teto garantido. Smoke usa ação manual em SQLite, sem chamada a provedor. Quando necessário, `tokenizer_path` referencia o vocabulário já preparado localmente: ele entra no hash e no snapshot. A execução de smoke bloqueia conexões; download público de vocabulário é preparação separada, não chamada a modelo.
- MatrAIx: CLI real `matraix smoke` para Survey/Chat e `matraix run -c recipe --max-cost-usd teto` para jobs. `runtime_root`, `recipe`, `model` e `credential_refs` são declarados. O número de combinações agente×tarefa×tentativa deve corresponder ao preflight. Web/OS-app dependem de Docker e requisitos do upstream. A saída preserva arquivos de evidência de tarefa; manifesto sem respostas não vira conclusão de pesquisa.

Credenciais são referências de variáveis de ambiente permitidas, nunca valores no JSON ou no chat. O subprocesso recebe apenas ambiente mínimo e as referências declaradas. Stdout do protocolo é JSON; logs arbitrários do provedor não são expostos. Timeout encerra o grupo de processos quando o sistema permite. Isso não comprova controle de cobrança fora do que a CLI upstream e o provedor efetivamente impõem; confira políticas do runtime e saldo antes de autorizar.

Uma execução comportamental exige tarefa pertinente, personas adequadas, interpretação de respostas/interações, denominadores, contraprovas e limites. Engines instalados e smokes técnicos não validam consumidores, oferta, mercado, segurança ou retorno financeiro. As licenças MIT dos upstreams devem ser preservadas quando houver cópia/distribuição; esta integração chama instalações opcionais, sem relicenciar o framework.
