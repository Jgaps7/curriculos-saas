import logging
import sys

# ======================================
# 🎯 Configuração de log global
# ======================================

LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] — %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger(name: str = "CurriculosSaaS", level: int = logging.INFO) -> logging.Logger:
    """
    Cria um logger padrão para API, worker ou Streamlit.
    """
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evita duplicação de handlers
    if not logger.handlers:
        logger.addHandler(handler)

    return logger


# Exemplo de uso global:
logger = setup_logger("backend")
