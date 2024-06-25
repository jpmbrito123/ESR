# Over-the-Top (OTT) Multimedia Delivery Service

Este projeto visa o desenvolvimento de um protótipo de serviço de entrega de multimédia OTT (Over-the-Top), utilizando o emulador CORE como bancada de testes. O objetivo é criar uma rede overlay aplicacional para a transmissão eficiente de áudio, vídeo e texto em tempo real, a partir de um servidor de conteúdos para um conjunto de N clientes. A implementação se dará em etapas que englobam desde a preparação inicial até a construção de fluxos de dados otimizados, monitoramento de servidores, e estratégias de recuperação de falhas.

## Estrutura do Projeto
### Preparação das Atividades

- Escolha da linguagem de programação.
- Configuração da topologia de testes no emulador CORE.
- Definição do protocolo de transporte (TCP ou UDP).
- Implementação inicial de um cliente/servidor simples.

### Construção da Topologia Overlay com Árvore Partilhada

- Desenvolvimento de uma aplicação (oNode) que atua como cliente e servidor.
- Testes com envio e recepção de mensagens.
- Implementação de estratégias para a construção da rede overlay.
- Manutenção das ligações entre o RP e os servidores.
### Serviço de Streaming

- Implementação de cliente e servidor de streaming baseados em exemplos.
- Adaptação do código para leitura e transmissão de vídeos.
- Utilização de codecs adicionais e diferentes vídeos para testes.
### Monitorização dos Servidores de Conteúdos

- Troca de mensagens de prova entre o RP e os servidores.
- Cálculo e uso de métricas para determinar o servidor mais adequado para a difusão de conteúdos.
### Construção dos Fluxos para Entrega de Dados

- Minimização do tráfego gerado na rede.
- Implementação de estratégias para gerenciar os fluxos de transmissão de conteúdo.
### Métodos de Recuperação de Falhas e Adição de Novos Nós

- Estratégias para recuperação de falhas na rede overlay.
- Suporte para a adição de novos nós à rede.
