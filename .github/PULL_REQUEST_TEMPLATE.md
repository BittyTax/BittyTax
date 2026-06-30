Closes #

## Description

<!-- Briefly describe what this PR does and why. -->

## Checklist

- [ ] All CI checks pass (`isort`, `black`, `flake8`, `pylint`, `mypy`, `pytest`)
- [ ] Spell check passes (`pylint --spelling-dict=en_GB .`)
- [ ] CHANGELOG entry added
- [ ] Manually tested the changes

**For parser PRs only** _(skip if not applicable)_**:**
- [ ] Existing export files still parse correctly (backward compatibility maintained)
- [ ] Parser balances correctly — verified final balances using `bittytax_conv --format CSV sample.csv | bittytax --audit --nopdf`
