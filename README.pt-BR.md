# AWS Serverless Blueprints

> Serverless é uma arquitetura com modos de falha próprios, não "só faça deploy de uma função." Um
> catálogo das formas recorrentes de workload serverless na AWS — cada uma honesta sobre statelessness,
> entrega at-least-once, cold starts e least privilege. Documentado primeiro, implementado em público.

[![Fase](https://img.shields.io/badge/fase-1%20design-blue)](./ROADMAP.md)
[![ADRs](https://img.shields.io/badge/ADRs-5-green)](./docs/adr)
[![Blueprints](https://img.shields.io/badge/blueprints-4-blueviolet)](./docs/blueprints)
[![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-lightgrey)](./LICENSE)

Serverless é vendido como simplicidade — sem servidores, só funções — e é justamente esse enquadramento
que faz times entrarem despreparados nos seus modos de falha. Uma função é stateless e efêmera, então
estado guardado nela desaparece. Fontes de evento entregam pelo menos uma vez, então um handler não
idempotente processa em duplicidade. Cold starts e limites de concorrência são o modelo real de
latência e custo, invisíveis até o tráfego encontrá-los. E uma função com uma role ampla é um raio de
explosão amplo. Nada disso é exótico; tudo é padrão, e tudo é pulado pelo "só faça deploy de uma
função."

Este repositório é um catálogo das formas de workload serverless que de fato recorrem — uma API
síncrona, um fan-out assíncrono, um workflow orquestrado, um job agendado — cada uma descrita como
blueprint: quando usar, como é estruturada na AWS, e como falha. Os modos de falha não são um apêndice;
são o ponto.

**English:** [README.md](./README.md)

---

## O que já existe

| Área | Status | Link |
| --- | --- | --- |
| Contexto e escopo | Pronto | [docs/context.md](./docs/context.md) |
| Catálogo de blueprints | 4 blueprints | [docs/blueprints](./docs/blueprints) |
| Notas Well-Architected | Pronto | [docs/well-architected-notes.md](./docs/well-architected-notes.md) |
| Diagramas de arquitetura | Pronto | [docs/diagrams](./docs/diagrams) |
| Registros de Decisão de Arquitetura | 5 publicados | [docs/adr](./docs/adr) |
| Deployments de referência | Planejados — Fase 3 | [ROADMAP.md](./ROADMAP.md) |

## A ideia

**Escolha o blueprint para a forma do workload, e herde as verdades serverless que toda forma respeita.**
Os blueprints diferem; quatro fatos transversais, cada um um ADR, não:

- **Funções são stateless e efêmeras** — estado vive num store gerenciado (DynamoDB, S3), nunca na
  memória ou disco da função entre invocações.
- **Entrega é at-least-once** — fontes de evento fazem retry, então todo handler é idempotente e todo
  caminho assíncrono tem uma dead-letter queue. Exactly-once é algo que você constrói.
- **Cold start e concorrência são o modelo de custo/latência** — são projetados em torno (provisioned
  concurrency onde latência importa, limites de concorrência onde um downstream precisa de proteção),
  não descobertos num incidente.
- **Cada função tem sua própria role de menor privilégio** — uma função, uma role, permissões mínimas —
  para que o raio de explosão de uma função comprometida seja limitado por construção.

## Os blueprints

| Blueprint | Forma | Use quando |
| --- | --- | --- |
| [Synchronous API](./docs/blueprints/synchronous-api.md) | API Gateway → Lambda → store | Um cliente espera uma resposta |
| [Asynchronous fan-out](./docs/blueprints/async-fanout.md) | Evento → fila/tópico → Lambda | O trabalho pode ocorrer após a resposta, ou em paralelo |
| [Orchestrated workflow](./docs/blueprints/orchestrated-workflow.md) | Step Functions sobre Lambdas | Um processo multi-etapa precisa de estado, retries e visibilidade |
| [Scheduled / batch](./docs/blueprints/scheduled-batch.md) | Agenda → Lambda sobre um dataset | O trabalho roda por relógio, não por request |

Cada página de blueprint tem as mesmas cinco seções — intenção, estrutura, quando / quando não, modos de
falha, as verdades serverless que honra — para serem comparáveis, e para que o "quando não" honesto
nunca seja pulado.

> Os documentos técnicos são mantidos em inglês para alcançar o público mais amplo possível.
> Este README traz o contexto em português.

## Roadmap

Quatro fases, acompanhadas como milestones no GitHub. Detalhes em [ROADMAP.md](./ROADMAP.md).

1. **Blueprints** — as quatro formas, seus modos de falha, os diagramas, os ADRs
2. **Contratos** — as convenções de evento, idempotência e role IAM que todo blueprint compartilha
3. **Deployments de referência** — cada blueprint como infraestrutura-como-código para deployar
4. **Drills de resiliência** — forçar retries, cold starts e throttling; mostrar cada blueprint aguentando

## Relacionados

- [serverless-ai-cicd-templates](https://github.com/prodrigues2023/serverless-ai-cicd-templates) — como esses blueprints são deployados com segurança: OIDC, promoção de artefato, entrega de menor privilégio
- [event-driven-dotnet-reference](https://github.com/prodrigues2023/event-driven-dotnet-reference) — os padrões de messaging neutros (outbox, consumidores idempotentes) que os blueprints assíncronos aplicam
- [iot-realtime-ingestion](https://github.com/prodrigues2023/iot-realtime-ingestion) — um design de ingestão de alto throughput que o blueprint de fan-out assíncrono generaliza

## Autor

Paulo Roberto Franco Rodrigues — AI Solutions Architect.
Recentemente projetou frameworks corporativos de IA e atuou em comitê de arquitetura de IA definindo
os padrões de engenharia que trazem disciplina de software para a entrega de IA.
[LinkedIn](https://linkedin.com/in/paulo-roberto-franco-rodrigues)

## Licença

MIT — veja [LICENSE](./LICENSE).
