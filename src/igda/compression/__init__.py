from igda.compression.base import Compressor
from igda.compression.registry import (
    get_compressor,
    list_compression_ids,
    list_compressions,
    run_compression,
)

__all__ = [
    "Compressor",
    "get_compressor",
    "list_compressions",
    "list_compression_ids",
    "run_compression",
]
