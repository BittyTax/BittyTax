from bittytax.config import config
from bittytax.t_row import TransactionRow


def test_parse() -> None:
    config.ccy = "GBP"

    t_row = TransactionRow(
        [
            "Withdrawal",
            "",
            "",
            "",
            "0.2561",
            "ETH",
            "",
            "0.001072372581795762",
            "ETH",
            "1.63",
            "",
            "2022-05-20T22:32:11",
            "",
        ],
        1,
    )
    t_row.parse()

    assert str(t_row.t_record) == (
        "Withdrawal 0.2561 ETH + fee=0.001072372581795762 ETH (£1.63 GBP) '' "
        "2022-05-20T22:32:11 UTC "
    )
