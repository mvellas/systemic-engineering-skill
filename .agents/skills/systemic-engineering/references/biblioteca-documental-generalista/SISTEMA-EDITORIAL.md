---
date: 2026-10-28
updated: 2026-10-28
type: editorial-system
tags: [venture-lab, documentos, estilo]
sensitivity: personal
ai-first: true
---

## For future Claude
Sistema editorial dos modelos de Disruptive Venture Lab. As medidas propostas são decisões de adaptação, não medidas reproduzidas dos PDFs de referência. Ler o modelo específico antes de diagramar.

# Sistema editorial, gráficos e imagens

## O que foi observado e o que foi proposto

Os originais usam fundo branco, texto preto, identificação discreta no alto à direita, título centralizado, subtítulos em negrito, listas e tabelas. A extração identifica principalmente Calibri/Arial, corpo em torno de 11–12 pt, títulos frequentemente em 14 pt e identificação em 10 pt; alguns documentos usam outras fontes. Há variações por arquivo, registradas em `inventario-fontes.json`. Não há uma identidade editorial inteiramente uniforme.

A proposta abaixo conserva a sobriedade e a hierarquia, amplia a legibilidade e organiza mapas inteiros em uma prancha. Os SVGs são desenhos novos com conteúdo generalista; não são cópias das imagens originais.

## Página e hierarquia

| Elemento | Especificação sugerida | Quando adaptar |
| --- | --- | --- |
| Relatório narrativo | A4 retrato, margens de 18–22 mm | Ajustar à marca e ao meio de entrega |
| Matriz ou mapa | A3 paisagem ou prancha digital 1200 × 760 | Em A4, dividir por blocos com cabeçalho repetido, sem reduzir letras excessivamente |
| Corpo impresso | 11–12 pt, entrelinha 1,3–1,5 | Anexos podem ser menores se ainda legíveis a 100% |
| Título principal | 20–28 pt; máximo de duas linhas preferencialmente | Título deve dizer o documento e o recorte |
| Seções | 14–18 pt, peso médio ou negrito | Usar no máximo três níveis de hierarquia |
| Tabela | Cabeçalho discreto, texto alinhado à esquerda, números à direita | Repetir cabeçalho em continuação; evitar linhas divididas |
| Cabeçalho | Nome do negócio e identificação curta do documento | Sem repetir marcas do caso-fonte |
| Rodapé | Página, versão, data-base e classificação de circulação | Incluir fonte da figura perto dela, não apenas no rodapé |
| Fonte | Arial, Calibri, Aptos ou alternativa disponível e licenciada | Preferir uma família principal; o HTML usa Arial e Georgia no título |

Títulos devem permanecer com o primeiro parágrafo; uma ficha de momento da verdade não deve ser separada do evento que descreve. Matrizes SWOT, Canvas e árvores devem preservar a visão conjunta, com detalhes no anexo. Não esticar uma tabela ilegível para fingir que cabe em uma página.

## Paleta e semântica

| Função | Cor proposta | Regra |
| --- | --- | --- |
| Texto | `#20282c` | Contraste e clareza |
| Texto secundário | `#57626a` | Fontes, notas e unidades |
| Linhas | `#c8d1d4` | Estrutura discreta |
| Destaque | `#255b65` | Navegação, títulos de chamadas e decisões |
| Fundo de quadro | `#eff5f4` | Agrupamento sem sugerir julgamento |
| Papel | `#ffffff` | Fundo de leitura |

Uma cor não substitui uma palavra. Se houver status, escrever “hipótese”, “observado”, “pendente” ou equivalente. Cores de risco e desempenho precisam de legenda e critério definidos. Não transformar verde em sinal de aprovação quando nada foi validado.

## Linguagem

Começar pelo que o leitor precisa decidir. Explicar o mecanismo antes da recomendação. Usar títulos concretos, frases curtas e listas paralelas. Em cada afirmação relevante, separar:

- observado: o que uma fonte ou coleta permite afirmar;
- hipótese: premissa ainda não demonstrada;
- inferência: interpretação construída a partir de dados ou hipóteses;
- simulado: resultado de execução com configuração e limites identificados;
- desconhecido: informação ausente.

Não usar “sempre”, “garantido”, “sem risco” ou “à prova de fraude” sem fundamento específico; em geral, descrever condição, comparação e limite. Não copiar o argumento de segurança, o público, os parceiros, as jurisdições ou a monetização do caso-fonte.

## Contrato mínimo de qualquer visual

Cada figura final contém título que diga o que mostra, população ou escopo, período/data-base, unidade, fonte, classificação da evidência e uma legenda interpretativa. Deve haver uma tabela ou descrição textual equivalente. Uma imagem bonita não substitui a descrição dos dados.

Os SVGs fornecidos são wireframes: caixas e colchetes indicam onde entra o conteúdo. Posições, janelas e quantidades de caixas não representam uma medição nem um prazo real. Editar ou repetir componentes conforme o negócio; não apagar a indicação de lacuna para sugerir conclusão.

## Especificação dos gráficos quantitativos

| Pergunta | Visual | Dados mínimos | Eixos e regra de leitura |
| --- | --- | --- | --- |
| Qual alternativa entrega melhor resultado? | Barras ou pontos por cenário | cenário, métrica, valor, unidade, período, fonte/classificação | X = categoria; Y = uma unidade. Barras partem de zero; valores negativos permanecem negativos |
| Como o caixa evolui? | Linha temporal com tabela equivalente | período ordenado, saldo inicial, entradas, saídas, saldo final, moeda | X = tempo real; Y = saldo na moeda declarada; mostrar linha de zero e saldo negativo |
| Quais premissas mudam a decisão? | Tornado ou tabela de sensibilidade | parâmetro, valor-base, faixa testada, resultado-base e resultado alterado, método | Efeito sobre uma métrica de mesma unidade. Variação declarada; não usar larguras arbitrárias |
| Onde se perde conversão? | Barras de etapas ou funil | coorte, período, elegíveis, iniciaram, concluíram e denominadores | Taxas entre etapas da mesma coorte; etapas com públicos distintos não formam conversão válida |
| Quais riscos acompanhar primeiro? | Heatmap qualitativo | risco, rubrica de probabilidade/impacto, horizonte, classificação, responsável | Eixos ordinais rotulados; desconhecidos fora da matriz; não interpretar área como perda financeira |
| Qual a distribuição de resultados simulados? | Intervalos ou histograma | execução, seed, réplicas, métrica, unidade, amostra de resultados | Explicar quantis em linguagem comum; distribuição simulada não é probabilidade validada de sucesso |
| Há diferença regional? | Tabela ou mapa de regiões | geografia identificada, valor, fonte, período, unidade e cobertura | Ausência de dado é “não medido”; não preencher com zero nem deslocar marcador decorativo |

### Relações econômicas a explicitar quando pertinentes

Receita pode ser preço × unidades, assinaturas × preço por período ou outra regra contratual; declare a função antes de calcular. Contribuição = receita na base escolhida − custos variáveis na mesma base. Lucro precisa explicitar as despesas e tributos considerados. Caixa final = caixa inicial + entradas − saídas, conciliado por período. Investimento e custo econômico de esforço não são automaticamente saídas de caixa recorrentes.

Ponto de equilíbrio por unidade só é calculável com contribuição unitária positiva e estrutura de custo compatível: custos fixos do período / contribuição por unidade. Payback depende de fluxo acumulado, não apenas de dividir investimento pela receita. ROI requer definição do numerador, capital no denominador, horizonte e tratamento das entradas/saídas. Se a informação não existe, registrar lacuna; esses modelos não constituem recomendação financeira pronta.

## Diagramas estruturais

| Diagrama | Regras |
| --- | --- |
| Árvore PBS | Relação de composição: produto/serviço → partes; substantivos e critérios de aceitação |
| Árvore WBS | Escopo → entregas/pacotes de trabalho; não representa ordem temporal |
| Árvore institucional | Tipo de nó e de relação explícitos; não deduz participação societária |
| Roadmap | Tempo →, trilhas ↓, marcos e dependências; datas ou janelas relativas consistentes |
| Jornada | Ações do cliente em sequência, canais e fricções; explicitar recorte |
| Blueprint | Etapas alinhadas à jornada, raias e linhas de interação/visibilidade; o invisível fica abaixo da linha de visibilidade |
| RACI | Entrega × papel; letras com legenda, um A e pelo menos um R por linha |
| Canvas | Nove blocos em uma visão; detalhe e evidência em anexo |
| Proposta de valor | Perfil do cliente e mapa da oferta distintos; conectar por necessidade/mecanismo, não por alegação vaga |

## Imagens: briefing para qualquer negócio

Antes de produzir ou escolher uma imagem, preencher:

| Campo | O que definir |
| --- | --- |
| Função | Que informação a imagem ajuda a entender |
| Conteúdo | Pessoa, objeto, ambiente ou ação realmente pertinente |
| Origem | Foto própria, banco licenciado, ilustração original ou geração identificada |
| Direitos | Fonte, licença ou autorização necessária para o uso pretendido |
| Fidelidade | Real, protótipo, conceito ou representação ilustrativa |
| Composição | Proporção, enquadramento, espaço para rótulo, fundo e tamanho mínimo |
| Coerência | Estilo, traço, luz e personagens consistentes em uma sequência |
| Acessibilidade | Texto alternativo que descreve a informação, não apenas a aparência |
| Limites | Sem dados privados, depoimentos inventados, logotipos de supostos parceiros ou interface inexistente apresentada como real |

Brief reutilizável: “Produzir [tipo de imagem] para explicar [ação ou conceito] a [audiência]. Mostrar [elementos necessários] em [contexto], com [proporção e enquadramento]. Aplicar [paleta e estilo]. Identificar como [real/conceito/ilustrativo]. Não inserir números, nomes, selos ou marcas que não tenham sido fornecidos e autorizados.”

Para persona, avatar é suficiente; para jornada, usar ações visuais consistentes; para arquitetura, árvore, RACI, SWOT, risco, roadmap e viabilidade, diagramas ou gráficos são mais informativos que fotos. Nenhum modelo exige uma imagem decorativa.

## Antes da entrega

Verificar legibilidade a 100%, cortes de tabela, rótulos longos, contraste, ordem de leitura, legenda, fontes, correspondência numérica e coerência entre texto e gráfico. Os HTMLs permitem leitura responsiva e impressão. Para pranchas densas, preferir SVG ou PDF de pranchas em paisagem. Revisão estrutural não substitui leitura por alguém que precisa tomar a decisão.
