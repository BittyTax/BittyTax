# Resource Files

`bittytax.conf.template` is the bundled source template used to create a user's real config file.

Do not edit `bittytax.conf.template` if you want to change BittyTax's active configuration. Edit the real config file in the BittyTax data directory instead:

- `~/.bittytax/bittytax.conf`
- `$BITTYTAX_DATA_DIR/.bittytax/bittytax.conf`

The template is only copied when that real config file does not already exist.