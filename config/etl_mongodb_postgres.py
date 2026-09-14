"""Compatibilidade: encaminha a antiga carga Feira para o DW dimensional oficial."""
import importlib.util
from pathlib import Path


def main():
    caminho = Path(__file__).with_name("5_etl_mongodb.py")
    spec = importlib.util.spec_from_file_location("etl_feira", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.executar_etl()


if __name__ == "__main__":
    main()
