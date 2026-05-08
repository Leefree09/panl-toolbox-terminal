"""PANL Toolbox Terminal — public CLI for the PANL container format.

This package is the user-facing CLI. The on-disk format work
(reader, writer, encoder, validator) is performed by the reference
implementation that historically ships under the ``kpow`` package
name. This wrapper presents PANL naming throughout while delegating
to that engine internally.
"""

__version__ = "1.0.0"
