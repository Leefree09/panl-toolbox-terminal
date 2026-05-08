"""Command implementations for the ``panl`` CLI.

Each module exposes a ``register(subparsers)`` entry point that adds
its subcommand to the top-level parser, plus the actual ``run(args)``
implementation. Keeping each command isolated makes the public CLI
shape easy to audit.
"""
