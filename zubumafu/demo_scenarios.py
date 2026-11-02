"""Transparent validation prompts, never fabricated model conversations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    description: str
    prompts: tuple[str, ...]
    expected: tuple[str, ...]


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "catalog", "Catálogo e cordas",
        "Orçamento, disponibilidade e diferenças entre nylon e aço.",
        ("Quais violões disponíveis custam até R$ 1.000?", "Quais dessas opções têm cordas de aço?"),
        ("Até três opções reais com preço e disponibilidade verificados.",
         "Sem presumir nível musical nem chamar as opções de 'melhores'.",
         "Nylon e aço identificados individualmente pelas especificações."),
    ),
    Scenario(
        "pix", "Promoção e PIX",
        "Preço de tabela, promoção ativa e desconto não cumulativo.",
        ("Quanto custa o Kalani KAL-700T Tenor Natural?",
         "E pagando no PIX, fica mais barato?",
         "Ele entra em um orçamento de R$ 340?"),
        ("Preço de tabela R$ 359,00; promoção 10%; final R$ 323,10.",
         "Não existe desconto PIX adicional com promoção ativa.",
         "Filtro de orçamento usa o preço final."),
    ),
    Scenario(
        "returns", "Troca e devolução",
        "Política do PDF e esclarecimentos antes de orientar.",
        ("Comprei um instrumento e me arrependi. Posso devolver?", "Comprei pela internet."),
        ("Consulta à seção correta do manual.",
         "Solicita informações faltantes sem presumir elegibilidade.",
         "Não confunde previsão de entrega com data de recebimento."),
    ),
    Scenario(
        "orders", "Acompanhar pedido",
        "Conferência demonstrativa de pedido e e-mail, sem expor terceiros.",
        ("Quero consultar meu pedido.",),
        ("Pede número e depois e-mail, um dado por vez.",
         "Somente após a conferência retorna o total histórico e os itens.",
         "Não altera pedido nem inventa rastreamento."),
    ),
    Scenario(
        "missing", "Produto indisponível",
        "Distinguir modelo cadastrado e disponibilidade.",
        ("Vocês têm o Shelby SN-7C 7 Cordas Nylon Natural?",),
        ("A fonte mostra o produto como descontinuado, sem estoque.",
         "Não sugere que está disponível; não inventa outra versão."),
    ),
    Scenario(
        "unknown", "Produto desconhecido",
        "Não transformar produto fictício de teste em item da loja.",
        ("Vocês vendem a guitarra Zubumafu X-999?",),
        ("Admite ausência de registro nos CSVs.",
         "Não inventa especificações nem preço."),
    ),
    Scenario(
        "outside", "Fora do escopo",
        "Redirecionamento breve sem fatos comerciais inventados.",
        ("Qual é a previsão do tempo para amanhã?",),
        ("Explica gentilmente o escopo musical da loja.",
         "Sem chamada desnecessária a ferramentas de comércio."),
    ),
)

SCENARIO_BY_KEY = {scenario.key: scenario for scenario in SCENARIOS}
