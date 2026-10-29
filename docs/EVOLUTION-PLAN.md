# Evolução do framework — auditoria e plano

Baseline auditada: `9d540d21d8c134a05b26ba8018828cd2ce7b2509` (main remoto em 28/10/2026). Os 46 testes existentes passaram antes de qualquer mudança. Implementação em branch separada; commit, push e merge autorizados pelo usuário em 29/10/2026.

## Lacunas verificadas

| Área | Existente | Lacuna / solução proposta |
| --- | --- | --- |
| Fases e autoridade | CLI sef.py, nove fases, autoridades por identidade/escopo, rejeição, hashes, reopen, STPA e Halligan | Preservar contratos e testes; incluir dados novos nos hashes quando o módulo for habilitado |
| Entrevistas | Instruções VFT/SSM e perguntas de requisitos pendentes | Rodadas persistidas, perguntas de acompanhamento, tipos de resposta, conflitos e relações rastreáveis |
| Pesquisa | Registro CSV e orientação metodológica | Registro de alegações/evidências externas, plano de pesquisa, captura autorizada, integridade e triangulação |
| Análise | VFT, SSM e STPA conceituais, sem motor de comparação | MCDA com critérios, pesos humanos, veto, sensibilidade e decisão pendente |
| Simulação | Nenhum motor no repositório auditado | Motores locais, preflight, autorizações separadas, resultados imutáveis e adapters opcionais reais |
| Predição | Ausente | Baseline supervisionada com holdout; otimização de substituto e integração BDH experimental sem alegação de validação de mercado |
| Produtos | Templates de engenharia Markdown/CSV | Biblioteca generalista e relatório/dashboard HTML navegáveis com fontes, gráficos e interpretação aplicada |
| Portabilidade | Scripts Python sem dependências, skill em .agents | Preservar CLI; pacote reproduzível para executor sem terminal e módulos opcionais isolados |

## Arquitetura

`sef.py` mantém os comandos e gates existentes. `scripts/sef_runtime/` adiciona persistência e auditoria, entrevistas, pesquisa, decisão, simulação e relatórios. Um documento estruturado opcional em `.systemic-engineering/08-consulting/model.json` concentra a análise; fontes e runs guardam hashes e snapshots. As fases originais continuam sendo intake → vft → ssm → reconcile → stpa → requirements → planning → execution → closure. Pesquisa e simulação são capacidades transversais, não atalhos para avançar gates.

Os comandos novos não fabricam aprovação metodológica nem de fase. Revisão de método, aprovação de fase e autorização de execução têm registros distintos. Autorizações de execução são vinculadas ao hash da configuração e dos arquivos referenciados, escopo, autoridade, custo e uso único. Mudança de premissa torna produtos e aprovações dependentes antigos; outputs antigos são preservados.

## Roadmap priorizado e condições de aceite

1. P0 — base compatível, integridade, bloqueios e fontes: testes legados passam; dados inválidos e autorização antiga não executam.
2. P1 — entrevistas e pesquisa: rodadas sem repetição cega, distinção de fatos/declaracões, conflitos visíveis e fonte externa obrigatória para alegação externa.
3. P1 — motores e comparação: sementes reproduzíveis, custo e parâmetros limitados, cenário de falha, MCMC com diagnóstico, ponderação transparente.
4. P1 — relatório: todos os documentos aplicáveis, fontes clicáveis, explicações específicas, plano de ação/Gantt, consistência entre relatório e dashboard.
5. P2 — externos e aprendizado: OASIS/MatrAIx chamam APIs/CLI oficiais; BDH usa implementação oficial identificada. Ausência de infraestrutura produz bloqueio ou smoke explicitamente técnico.
6. P2 — exemplos software/negócio/sistema crítico, testes adversariais, navegador e pacote para executor. Exemplos são fixtures, nunca aprovações de projeto real.

## Fundamento científico e limites

Fluxo: pergunta decisória → hipótese falsificável → desenho de pesquisa/experimento → evidências externas → modelo explícito → diagnóstico/validação → alternativas → recomendação condicional → teste real. Método, dados e inferências ficam distinguíveis. Sem observações de resultados comerciais não existe probabilidade calibrada de sucesso. Treinar e otimizar um modelo de dados sintéticos não valida sua correspondência com o mercado.

Fontes metodológicas concretas e contratos das integrações ficam em `references/scientific-method.md`. A documentação deste repositório descreve implementação; não serve como prova externa de demanda, segurança, eficácia ou conformidade.

## Integração entregue na versão 3.0

O router cobre investigação empresarial e engenharia, preservando fases e gates. `experiments.py` prepara desenhos, `campaigns.py` acompanha execuções individualmente autorizadas, `finance.py` calcula caixa/VPL sob premissas explícitas, e relatórios usam os mesmos resultados. Modelo financeiro e resposta a preço são opcionais, com campos e fontes validados. Campanhas incompletas não recebem candidato final; comparação é triagem de robustez, sem distribuição de probabilidades implícita entre cenários.

A biblioteca documental distribuída usa identificadores anônimos para o corpus de referência; os originais locais e resultados privados não entram na publicação. A licença original do repositório é preservada. Os exemplos são reproduzíveis, sintéticos e sem aprovação real de cliente. Evidências de aceitação e limites ficam em [VALIDATION.md](VALIDATION.md).
