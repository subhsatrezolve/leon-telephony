"""Bot module for the hotel booking bot.

The runtime entrypoint for this project is the ElevenLabs HTTP API
defined in `main.py`, which imports tools from `src.bot.tools`.

The previous LiveKit/pipecat voice pipeline and multi-agent runtime
have been removed in favor of ElevenLabs hosted agents plus HTTP tools.
This module is intentionally minimal and does not currently export any
runtime helpers.
"""

__all__: list[str] = []
