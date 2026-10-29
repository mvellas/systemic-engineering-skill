# Validação da versão 3.0 — 29/10/2026

Evolução desenvolvida em `feat/evidence-consulting-framework`, a partir de `9d540d21d8c134a05b26ba8018828cd2ce7b2509`. Commit, push e merge autorizados pelo usuário. A aprovação para publicar código não aprova decisões de clientes nem autoriza simulações externas.

## Evidências

| Verificação | Resultado observado |
|---|---|
| Suíte completa | 97 testes passaram em 133,211 s; 46 testes originais preservados |
| Regressão financeira adicional | 8 testes de viabilidade passaram, incluindo exportação CSV com cenários financeiros e simples no mesmo experimento |
| Navegador Chromium | 12 verificações passaram: três projetos, relatório e dashboard, larguras de 1440 e 390 pixels; inclui seleção de valores a receber e gráficos de campanha |
| Skill e verificações estáticas | Validador da skill, compilação Python, sintaxe JavaScript, Ruff E9/F63/F7/F82, links Markdown locais e `git diff --check` passaram |
| Exemplo de negócios com `--viability` | Dois experimentos originais e quatro casos multiagente financeiros executados como fixtures locais; fluxo até encerramento; sem aprovação real de cliente |
| Exemplo de software | Fluxo com aprovações de teste até encerramento |
| Exemplo crítico | Bloqueio em STPA sem autoridades qualificadas; nenhuma execução física |
| OASIS 0.2.5 | Smoke real com ações manuais, SQLite e rede bloqueada; sem chamada a modelo |
| MatrAIx 0.1.0 | Smoke real do comando de inspeção; não equivale a teste comportamental com provedor |
| BDH oficial identificado por hash | Backpropagation em 28 registros de treino e 12 de teste sintéticos; acurácia 41,67%, abaixo da referência de 50%; resultado negativo preservado |

Os três testes opcionais da última parte da tabela foram realizados durante o desenvolvimento desta evolução; não são novas campanhas de mercado e não demonstram desempenho comercial. Nenhum provedor pago foi usado. A comparação BDH não tem tamanho nem base empírica para concluir superioridade ou inadequação geral da arquitetura.

Recibos locais ignorados pelo Git: `.evidence/full-tests-final.log`, `viability-final.log`, `browser/results.json`, `optional-smokes/` e `*-release.json`. Os recibos `*-release.json` indicam os caminhos exatos de relatório, dashboard, manifesto e ZIP. A pasta `.evidence` e os projetos gerados não entram na publicação; exemplos executáveis e dados geográficos de referência entram.

## Cobertura

- Entrevistas de Intake, VFT e SSM com tipos de resposta, perguntas de acompanhamento, conflitos e projeções de decisões/rastreabilidade.
- Fontes e alegações externas com evidência, URLs, datas, independência, confiança, conflitos e captura autorizada; documentos próprios não contam como prova externa.
- Comparação MCDA com escalas e pesos humanos, vetos e sensibilidade; decisão continua humana.
- Motores locais de Monte Carlo, agentes, estoques/fluxos, propagação de falhas e MCMC; ML e BDH experimentais; adaptadores opcionais OASIS/MatrAIx.
- `sim plan` e campanhas com registro, próxima configuração, acompanhamento e comparação. Condições de mercado, escolhas e estruturas comportamentais ficam separadas. Não há probabilidade implícita entre casos nem autorização em lote.
- Financeiro opcional com investimento, CAPEX, dedução proporcional explícita sobre receita, recebimentos/pagamentos defasados, VPL, capital adicional, recuperação e saldos pendentes; resposta a preço opcional e assumida explicitamente.
- Relatório/dashboard responsivos e offline, rede registrada pelos agentes, mapa somente com dados regionais declarados, fontes, comparações, plano de ação, cronograma, 22 documentos individuais e ZIP.
- Aprovação de método, autorização de execução, gates de fase e revisão de cliente separados; hashes, auditoria, invalidação e tentativas falhas preservadas.

## Reprodução

```bash
python3 -m unittest discover -s tests -v
python3 examples/run_example.py --kind business --viability --output examples/output/negocio-novo
python3 examples/run_example.py --kind software --output examples/output/software-novo
python3 examples/run_example.py --kind critical --output examples/output/critico-novo
```

Os exemplos exigem diretório novo e recusam sobrescrever projetos. Para repetir as 12 verificações de navegador, gerar diretórios `business-SUFIXO`, `software-SUFIXO`, `critical-SUFIXO` dentro de `examples/output`, instalar os extras de desenvolvimento quando necessário e usar:

```bash
python3 tests/browser/check_reports.py --chromium CAMINHO_ABSOLUTO_CHROMIUM --suffix=-SUFIXO
```

O plano `examples/agent-experiment-plan.json` contém 81 combinações e 8.100 trajetórias **planejadas**. Não foi executado como campanha de mercado. Seus identificadores e números são demonstrativos; referências do projeto precisam ser registradas e entradas revisadas antes de qualquer execução real.

## Limites materiais

- Validação estrutural não autentica uma fonte nem sua pertinência. Diagnóstico e recomendação exigem pesquisa específica, contraprovas e revisão substantiva.
- Réplicas e intervalos Monte Carlo medem variação condicional; não calibram o modelo ao mercado. Redes e preferências sintéticas não substituem consumidores reais.
- O caixa de referência sem `finance` é simplificado. Com `finance`, continuam ausentes estoque, inadimplência, dívida, depreciação, regimes fiscais e valor terminal. VPL é truncado ao horizonte; saldos a receber/pagar são divulgados. Taxa de desconto pertence ao período declarado. Não é parecer contábil.
- Recuperação do investimento é o primeiro cruzamento do saldo acumulado; não garante ausência de perda posterior. Critério de sucesso deve ser explícito, e caixa final positivo não elimina insuficiência de caixa intermediária.
- Campanhas classificam um candidato pela pior condição de caixa p10 declarada, regra de triagem que não substitui objetivos VFT, vetos ou decisão humana. Validar candidatos em sementes e condições reservadas.
- Diagnósticos MCMC são preliminares. ML em dados simulados aprende o simulador; não demonstra previsão real. BDH permanece experimental, sem alegação de superioridade.
- OASIS comportamental fica limitado a servidor local compatível; chamadas pagas são recusadas sem controle estrito de faturamento. MatrAIx exige runtime, modelo, orçamento e autorização pertinentes.
- Captura HTML textual é representação UTF-8 com hash, não arquivo forense dos bytes HTTP. Captura de navegador tem limites contra mudanças de DNS e alvos adversariais exigem executor com controle de rede.
- Testado no macOS desta sessão; Windows/Linux e todos os harnesses não foram certificados por execução. Um ambiente sem terminal recebe pacote reproduzível, sem alegação de execução inexistente.
- Sistemas críticos continuam dependentes de especialistas e autoridades reais. Publicação de código não certifica segurança ou prontidão de qualquer cliente.
