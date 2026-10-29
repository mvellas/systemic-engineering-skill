---
date: 2026-10-28
updated: 2026-10-28
type: template-workflow
tags: [venture-lab, documentos, uso]
sensitivity: personal
ai-first: true
---

## For future Claude
Instruções para reutilizar a biblioteca documental de Disruptive Venture Lab. Não executar simulações ou alterar casos existentes para preencher estes modelos. Não pressupor integração automática ao runtime.

# Como aplicar a biblioteca em outro negócio

## Entradas e saídas

Comece por negócio, audiência, pergunta decisória, idioma, território, data-base, horizonte, fontes disponíveis e restrições. Escolha os documentos que respondem à pergunta. Não é necessário criar todos para qualquer ocasião; se a skill exigir avaliação de aplicabilidade, registre exclusões conforme o contrato vigente.

Cada item do catálogo entrega quatro recursos:

- `modelos/<nome>.md`: estudo do original, estrutura editorial, dicionário, brief visual, critérios de revisão e seção “Modelo preenchível”;
- `dados/<nome>.json`: entrada vazia com metadados, registros, proveniência, fontes, conclusão e revisão;
- `visuais/<nome>.svg`: composição vetorial editável com placeholders;
- `paginas/<nome>.html`: apresentação para consulta, preenchimento temporário e impressão.

O `catalogo.json` descreve os mesmos 22 modelos de forma estruturada. `inventario-fontes.json` contém nomes, hashes SHA-256, tamanhos e características de todas as páginas das fontes. Os originais permanecem na pasta de origem e não foram copiados para esta biblioteca.

## Sequência sugerida por dependência

1. Defina contexto, pergunta e fontes; prepare persona e carta de empatia como hipóteses quando não houver pesquisa.
2. Estruture proposta de valor e ofertas B2B/B2C pertinentes; reconcilie o Canvas.
3. Analise PESTEL, forças competitivas e SWOT; revise estratégia à luz do que foi encontrado.
4. Conecte jornada, momentos da verdade e blueprint, usando os mesmos identificadores de etapa.
5. Defina arquitetura e PBS; derive WBS, ciclo de vida, roadmap e RACI.
6. Consolide riscos e viabilidade; registre decisão, condição de reversão e próximo teste.
7. Produza a ficha institucional apenas quando houver necessidade de explicar marcas, unidades ou entidades.

A sequência é iterativa: uma descoberta pode exigir revisar documentos anteriores. Não preencher um documento com uma conclusão apenas porque outro já a afirmou.

## Tipos e ausência de dados

| Tipo | Convenção |
| --- | --- |
| texto | String não vazia quando conhecida |
| referência | ID de entidade ou registro; deve existir na instância ou fonte declarada |
| decimal | Número JSON, com unidade, moeda quando pertinente e período |
| inteiro | Número inteiro; ordem e nível não são métricas de desempenho |
| data | `YYYY-MM-DD`; desconhecida = `null` |
| enum | Um dos valores definidos na descrição do campo; desconhecido fica `null` ou enum explícito |
| lista | Array de IDs/itens conforme a descrição; vazio significa ainda sem registros |

O registro vazio incluído em cada JSON mostra as chaves a preencher. Duplique-o para novas linhas; não trate a sua presença como observação. `null` não é zero, falso nem “não aplicável”. Registros podem ter chaves não pertinentes: marque a não aplicação na versão humana e justifique se ela alterar a interpretação. O JSON é uma estrutura documental de entrada, não o schema canônico do runtime nem um arquivo pronto para `venture build`.

As tabelas de dicionário descrevem dados necessários, mas nem todos precisam estar disponíveis antes do primeiro rascunho. Para a versão final, campos essenciais à decisão devem estar preenchidos ou gerar uma conclusão explicitamente limitada.

## Proveniência e fontes

Cada registro inclui:

| Campo | Conteúdo |
| --- | --- |
| classificacao | observado, hipotese, inferencia, simulado ou desconhecido |
| fonte_id | Referência à lista de fontes ou à hipótese formal registrada |
| localizacao | Página, seção, célula, linha ou registro que permite conferir |
| data_base | Data ou período ao qual a afirmação se refere |
| data_consulta | Quando a fonte foi consultada |
| confianca | baixa, media, alta ou desconhecida, com justificativa na limitação |
| limitacao | Viés, recorte, insuficiência ou tarefa de coleta |

A lista `fontes` aceita objetos com `id`, `titulo`, `caminho_ou_url`, `localizacao`, `data_base`, `data_consulta`, `hash_opcional`, `o_que_sustenta` e `limitacoes`. Hipótese pode apontar para declaração do patrocinador ou registro de premissa. Uma inferência precisa indicar as entradas e a regra de interpretação. Resultado simulado deve identificar execução e configuração; não é pesquisa de mercado.

A `decisao` consolida síntese, justificativa, alternativas, condição de reversão, próximo passo, responsável e prazo. `revisao` só recebe resultado após avaliação real. `aplicabilidade` registra exclusão de documento, não autorização para inventar dados.

## Identificadores entre documentos

| Entidade compartilhada | Documentos relacionados | Regra de coerência |
| --- | --- | --- |
| Segmento/persona | B2B/B2C, Canvas, empatia e valor | Mesmo público e papel de pagamento |
| Etapa de interação | Jornada, momentos da verdade e blueprint | Mesma ação e fronteira de visibilidade |
| Componente | Arquitetura e PBS | Mesmo escopo e critério de aceitação |
| Pacote de trabalho | WBS, roadmap e RACI | Mesma entrega, responsável e dependência |
| Risco | Riscos, PESTEL, SWOT e viabilidade | Mesmo evento, efeito, gatilho e dono |
| Cenário | Viabilidade e estratégia | Mesmas premissas, unidade, moeda e período |
| Fonte/hipótese | Todos | A evidência não muda de classificação ao ser citada em outro documento |

## Adaptação por tipo de negócio

| Contexto | Ajuste necessário |
| --- | --- |
| Serviço profissional | Entregáveis, esforço humano, capacidade, revisão, prazo e margem por contratação |
| Varejo ou fabricação | Produto, estoque, fornecedores, perdas, reposição, logística e capital de giro |
| Assinatura ou SaaS | Receita por período, aquisição, ativação, retenção, suporte e custo de servir |
| Plataforma ou marketplace | Papéis e lados separados, quem paga, dependência de liquidez e regra de captura de receita |
| Organização sem receita comercial | Beneficiário, financiador, entrega de missão, custo por resultado e sustentabilidade |
| Operação física ou atendimento local | Ambiente, deslocamento, fila, capacidade, segurança e recuperação do serviço |

Não assumir aplicativo, equipamento, taxa de transação, número de funcionários, país, fornecedor ou mecanismo de segurança. Quando o modelo contém um termo pouco adequado, adaptar o termo preservando a pergunta que ele precisa responder.

## Produção e entrega

Copie a seção “Modelo preenchível” para uma instância do novo negócio e preencha os campos. Use o dicionário completo para criar tabelas ou anexos. Edite o SVG ou gere o visual a partir de dados identificados. Marque protótipos e imagens conceituais como propostas.

Os HTMLs são locais, sem bibliotecas remotas, fontes externas ou envio de dados. Campos `contenteditable` são temporários e **não persistem ao recarregar**; para manter uma versão, edite Markdown/JSON ou salve a impressão em PDF. Esta biblioteca não inclui aplicação com armazenamento nem sincronização de edições entre formatos.

A impressão dos HTMLs é A4; a prancha de um mapa denso deve preferencialmente usar o SVG ou `PRANCHAS-VISUAIS.pdf` em paisagem. A paginação de documentos finais preenchidos exige nova revisão, pois o volume de texto pode mudar.

## Relação com a skill existente

Biblioteca complementar e independente dos geradores. O contrato da skill e o modelo canônico continuam governando as instâncias que ela gerar. Para usar esta biblioteca numa sessão, indique: “Use os modelos de `references/biblioteca-documental-generalista` para preparar [documentos] para [negócio], com [fontes], sem herdar dados dos documentos de referência.”

A contagem 22 corresponde aos arquivos-fonte, não à contagem de artefatos do runtime. Há dois modelos de oferta, uma ficha institucional e um relatório de viabilidade específicos da organização da biblioteca. Nenhum módulo Python, caso, handoff ou aprovação de simulação foi alterado para criá-la.
