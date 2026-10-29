# Consultoria orientada por evidências — guia do agente

O agente conduz o fluxo com as ferramentas de seu harness e a CLI. O empresário responde às perguntas e toma decisões; não deve ser instruído a coordenar manualmente cada script. A análise específica é trabalho do agente: os comandos estruturam, verificam, calculam e apresentam, mas não transformam texto genérico em diagnóstico.

## Iniciar e retomar

Invocação: **Use $systemic-engineering para investigar esta ideia, entrevistar os envolvidos, comparar alternativas e preparar um relatório para decisão. Não execute gastos, testes físicos ou serviços externos sem autorização específica.**

1. Execute `sef.py status PROJETO` se houver estado. Não reinicialize. Caso novo: discuta escopo e inicialize com a anuência do responsável.
2. Habilite o módulo uma vez: `sef.py consult enable PROJETO`. Projetos existentes sem esse comando mantêm seu comportamento anterior.
3. `sef.py consult next PROJETO` prepara a rodada da fase atual e o plano de investigação. Apresente as perguntas em linguagem cotidiana; não despeje JSON ao empresário.
4. O agente executa a pesquisa pública com o navegador/conector disponível, registra fontes externas e contraprovas, importa respostas, escreve análises e apresenta decisões pendentes. As fases originais continuam sendo governadas pelos comandos `approve`, `pending`, `advance` e `reopen`.

Neste documento, `sef.py` significa `python3 <skill-dir>/scripts/sef.py`.

## Entrevistas que investigam

`interview next PROJETO --limit 3` retorna até três perguntas, alternativas, técnica, justificativa metodológica e contexto disponível. `interview answer PROJETO --config respostas.json` registra uma resposta por pergunta da rodada. Campos: `round_id`, `speaker`, `answers: [{question_id, kind, text, source_ids}]`.

Tipos: `fato` (com fonte registrada), `declaracao` (relato ainda não verificado), `desejo`, `preferencia`, `restricao`, `hipotese`, `decisao`. Decisão relatada em entrevista não vira aprovação de fase ou autorização de execução. Respostas vagas geram acompanhamento, limitado a cinco níveis; ao atingir esse limite, pare de insistir, registre a lacuna e proponha pesquisa ou observação. Não interprete esse limite como profundidade científica suficiente.

Em Intake, desafie problema, resultado observável, limite e representação dos afetados. Em VFT, use WITI, meios/fins, escala e trade-off; não atribua pesos pelo cliente. Em SSM, confronte transformação, CATWOE, visões conflitantes e viabilidade cultural. Personalize a formulação e explique consequências com as fontes do projeto. A seleção automática de perguntas é uma ajuda determinística; a interpretação contextual e o aprofundamento especializado continuam sob responsabilidade do agente.

Após a rodada, consulte os conflitos e as projeções `interview-trace.csv`/`interview-decisions.csv`. Entidades propostas ficam marcadas como candidatas, não objetivos aprovados. Para resolver um conflito: `consult resolve PROJETO --conflict CON-001 --resolution resolved|superseded|retained-with-dissent --by NOME --authority-id AUTH-ID --evidence REF --reason TEXTO`. Preserve a resposta anterior e o dissenso.

## Pesquisa e OSINT: conteúdo antes da citação

`research plan PROJETO` organiza mercado, concorrência, fornecedores, regras, comunicação e contraprovas. O agente pesquisa fontes primárias, notícias e fontes independentes conforme o assunto. Redes, blogs, anúncios, vídeos e reviews podem evidenciar o que alguém publica ou relata; não provam faturamento, gasto publicitário, conversão ou eficácia.

`research source PROJETO --config fonte.json` exige: `id` SRC-, `title`, `url`, `published_at`, `accessed_at`, `location`, `evidence`, `confidence` low/medium/high, `limitations`, `independence_group`. Acrescente `authority` e `source_type`. Datas são ISO ou `unknown`; isso não esconde a pendência. O registro guarda hash do trecho e sincroniza o source-register legado. Documento interno/autoral não é prova externa.

`research claim PROJETO --config afirmacao.json` exige `id`, `text`, `kind` observed/hypothesis/inference/simulated, `source_ids`, `limitations`; simulado exige `run_id`. Confronte texto com o trecho e sua população/período; uma citação existente não garante que sustenta a frase. A confiança deve explicar recência, método, independência e limites. Duas páginas da mesma origem não são triangulação independente.

`research audit PROJETO --as-of YYYY-MM-DD` sinaliza fontes antigas, dependência, capturas alteradas e conflitos. A data de consulta não é a idade do dado. Para preços e regras vigentes, pesquise novamente antes de aconselhar. Não resolver conflito apagando a contraprova.

### Capturas autorizadas

Para captura textual, configuração `{engine: "capture", url: "https://origem/pagina", cost_limit: 0}`. Registre revisão metodológica e autorização específica com `sim authorize`, depois `research capture PROJETO --config captura.json --grant GRANT-ID`. A conexão valida e fixa IP público; redirecionamento para outra origem exige nova autorização. Capturas são evidência bruta; ainda precisam de interpretação e registro de fonte.

Para screenshot real: `engine: "browser-capture"`, `url` e `allowed_origins` explícitas; mesmas duas autorizações e `research browser-capture`. Requer Playwright/Chromium opcional. O contexto é novo, sem cookies, sem JavaScript e permite somente GET/HEAD nas origens indicadas; recursos bloqueados podem alterar a aparência. Isso não certifica isolamento contra DNS rebinding: alvos adversariais exigem executor com firewall de egress. Não contornar login, bloqueios ou termos de acesso.

`research screenshot --capture CAMINHO` é diferente: produz imagem offline do texto de uma captura arquivada e se identifica como tal. Nunca chamá-la de screenshot do website vivo.

## Modelo único, análises aplicadas e templates

Use `consult import PROJETO --config analise.json` para atualizar apenas os campos permitidos. Nunca edite `08-consulting/model.json` diretamente: há integridade, revisões imutáveis, lock e journal de recuperação. `consult recover` repara interrupção de escrita; não remove lock de outro processo por conveniência.

Campos: problema; idioma; stakeholders; objetivos; alternativas; critérios; ações; riscos; relações; documentos; análise executiva e geografia opcional. Fontes, rodadas, respostas, runs e aprovações usam os comandos próprios. O exemplo `examples/run_example.py` demonstra os formatos; seus dados são explicitamente sintéticos.

Para cada um dos 22 modelos do [catálogo](biblioteca-documental-generalista/INDICE.md), registre aplicabilidade. Documento aplicável exige `finding` (achado específico), `mechanism` (explicação e limites), `implication` (consequência decisória), `source_ids` e `sections` com os títulos do modelo. Excluído exige `applicable: false`, `reason` e `reviewed_by`. Os SVGs de referência permanecem identificados como wireframes; o agente deve preencher ou construir os diagramas aplicados, sem apresentá-los como dados empíricos.

A análise executiva deve conter `diagnosis`, `recommendation`, `rationale`, `alternatives`, `reversal`, `next_test`, `limitations`, `confidence`, `confidence_reason`, `source_ids`. Um texto que serve igualmente para qualquer negócio não está concluído. Cada ação exige ID, título, dono, início, prazo, critério, orçamento quando pertinente e regra de parada. Marketing e comunicação devem decorrer do público e das evidências: mensagem, canal, oferta, hipótese, criativo proposto, métrica, prazo e orçamento; nenhuma campanha é lançada por produzir o plano.

Relações documentais devem ligar fontes, valores, objetivos, visões SSM, perdas/controles STPA, requisitos, alternativas e resultados. Relação documental não demonstra causalidade. Um mecanismo causal proposto deve indicar hipóteses e teste que o diferencie de explicações alternativas.

### Diagramas aplicados e arquivos individuais

Além das seções textuais, cada documento pode declarar `visual` com `type` flow/comparison/matrix, `title`, `classification`, `caption` e `source_ids`. Fluxo usa nós `{id,label}` e conexões `{from,to}`; comparação usa itens `{label,value}`, unidade e período; matriz usa `columns` e `rows`. O contrato verifica fontes, IDs e valores; o SVG é escapado e vem acompanhado de descrição/tabela. O agente deve escolher o visual que explica a decisão, não preencher figuras arbitrariamente. Seções adicionais de comunicação, canais, mensagem comercial e implementação são preservadas no relatório e nos Markdown individuais. Os wireframes dos modelos permanecem separados dos diagramas aplicados.

Cada pacote inclui `documentos/*.md` além dos capítulos HTML, dados e gráficos. Para revisão final: `consult review PROJETO --decision approved|rejected --by NOME --authority-id AUTH-ID --evidence REF --attestation "declaração humana sobre a entrega"`. Aprovação é recusada enquanto houver lacuna estrutural e permanece vinculada a modelo, resultados, código de apresentação e autoridades. Fixture não recebe status de entrega real. Rejeição posterior substitui a aprovação da mesma autoridade no mesmo snapshot. Nenhuma revisão final concede autorização de execução.

## Decisão e sensibilidade

`consult compare PROJETO` calcula um modelo aditivo transparente. Cada critério informa `id`, `weight` (soma 1), `min`, `max`, `direction` min/max, `judgment_by` e `weight_reason`; pode declarar `veto_below`/`veto_above`. Cada alternativa contém `scores: {criterio: {value, source_ids, explanation}}`, ganhos, perdas e objetivos afetados.

Antes de usar soma ponderada, verifique independência preferencial, escalas, duplicação de efeitos e adequação ao problema. A escala vem dos limites aprovados, não do melhor/pior candidato do lote. Veto não é compensado por outro benefício. A variação local de pesos é exibida; não representa análise global de todas as incertezas. O primeiro colocado é candidato consultivo, nunca decisão automática.

## Simulação: escolher, estimar, autorizar, executar, interpretar

1. `sim capabilities` identifica Python, memória física, CPU, pacotes, ferramentas e runtimes opcionais existentes. Não confunde instalação com disponibilidade de um modelo/servidor.
2. `sim select --problem uncertainty|adoption|stocks|failures|rate-estimation|prediction|sequence-research|social-network|persona-task` recomenda um engine com justificativa e fonte externa.
3. O agente prepara `experiment.json` com pergunta, fontes, modelo, cenários, seeds, escala, horizonte, custo, tempo e parada. Depois executa `sim preflight PROJETO --config experiment.json` e apresenta estimativas e limites.
4. Registre revisão do método: `sim authorize PROJETO --config experiment.json --kind method --by NOME --authority-id AUTH-ID --evidence REF --attestation "declaração humana e escopo"`.
5. Separadamente, após anuência específica: o mesmo comando com `--kind execution`. Ele retorna um `grant_id` de uso único. Revisão de método não autoriza execução; aprovação de fase não equivale a nenhum dos dois.
6. `sim run PROJETO --config experiment.json --grant GRANT-ID`. Arquivos referenciados e modelo entram no hash. A tentativa consome a autorização mesmo se falhar; mudança de dado/configuração exige nova revisão e autorização. Execução local ocorre em subprocesso com rede negada e timeout.
7. Leia resultados, não só manifestos. `consult interpret PROJETO --run-id RUN-ID --config interpretacao.json` exige `finding`, `mechanism`, `consequence`, `limitations`, `source_ids`, `reviewed_by`. Os dois HTMLs são regenerados juntos.

Em fixture, `--fixture` identifica aprovação fictícia e permite somente demonstrações locais limitadas, sem custo, BDH, captura ou engines externos. Isso não autentica uma pessoa real. Em risco alto/critico, revisão metodológica exige qualificação; os gates de fase existentes continuam exigindo os papéis independentes aplicáveis.

Para mercado e investimento, leia [market-feasibility.md](market-feasibility.md). O agente coordena campanhas com `sim campaign-register/next/status/analyze`, preservando autorizações por configuração; veja [agent-experiments.md](agent-experiments.md).

Leia [simulation-engines.md](simulation-engines.md) para os contratos numéricos e limites. Não escolher MCMC ou BDH apenas por sofisticação: explique qual pergunta concreta precisam responder.

## Produtos, revisão e portabilidade

`consult report PROJETO` produz um pacote imutável com `RELATORIO.html`, `DASHBOARD.html`, estudo JSON, qualidade e manifestos. `consult quality` retorna código 1 enquanto faltarem análises, fontes, interpretação ou ações. A checagem estrutural não aprova o conteúdo nem muda a fase. Revise como o destinatário: o que fazer, por quê, que perda pode ocorrer, o que invalidaria a recomendação e o que precisa acontecer na próxima semana.

Mapas só usam geometrias e valores regionais fornecidos com métrica, unidade, período, origem e classificação; regiões ausentes permanecem não medidas. Rede de agentes só mostra estados e contatos efetivamente registrados na simulação, em amostra identificada. Nunca animar marcadores geográficos ou interações como se fossem observações.

`consult impact` lista exports antigos e conflitos; os dados de consultoria entram nos hashes dos gates originais. Regenerar não reaprova. Outputs antigos ficam preservados. O histórico hash-encadeado detecta alterações locais, mas não é autenticação de identidade nem registro com assinatura externa.

Sem terminal: o harness prepara arquivos e um pacote para executor autorizado, sem dizer que executou. Com terminal, `consult bundle PROJETO --config experiment.json --output executor.zip` inclui skill, estado e dados declarados, excluindo segredos e capturas/runs. O executor verifica ambiente, preflight e novas autorizações. Copiar a pasta `.agents/skills/systemic-engineering` preserva recursos relativos em Claude Code, Codex, Antigravity e harnesses compatíveis; não há dependência de um fornecedor de LLM para os motores locais.
