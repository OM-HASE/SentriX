import chromadb
import logging

logger = logging.getLogger(__name__)

# =========================================
# LAZY CHROMADB INITIALIZATION
# =========================================
#
# FIX: Removed the "chromadb.PersistentClient | None" type
# annotation on _client. chromadb.PersistentClient is a
# factory function internally, not a class, so Python throws:
#   TypeError: unsupported operand type(s) for |: 'function' and 'NoneType'
# when it evaluates the annotation at module load time.
# Plain assignment with no annotation fixes it on all versions.
# =========================================

_client     = None
_collection = None

CHROMA_DB_PATH  = "./chroma_db"
COLLECTION_NAME = "repository_chunks"


def get_collection():
    """
    Returns the ChromaDB collection, initializing on first call.
    Raises RuntimeError with a clear message if it fails.
    """
    global _client, _collection

    if _collection is not None:
        return _collection

    try:
        _client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME
        )

        logger.info(
            "ChromaDB initialized at '%s', collection '%s' ready.",
            CHROMA_DB_PATH, COLLECTION_NAME
        )

        return _collection

    except Exception as exc:
        raise RuntimeError(
            f"ChromaDB could not be initialized at '{CHROMA_DB_PATH}'. "
            f"Check directory permissions. Original error: {exc}"
        ) from exc


class _CollectionProxy:
    """
    Proxy that forwards .add() and .query() to the lazily-initialized
    real ChromaDB collection. Keeps all existing import sites working.
    """

    def add(self, **kwargs):
        return get_collection().add(**kwargs)

    def query(self, **kwargs):
        return get_collection().query(**kwargs)

    def count(self):
        return get_collection().count()

    def peek(self, limit=10):
        return get_collection().peek(limit=limit)


collection = _CollectionProxy()