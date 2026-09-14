import re
from datetime import datetime
from pathlib import Path


def converter_to_date(match):

    data_str = match.group(1)

    try:

        data_convertida = (
            datetime.strptime(
                data_str,
                "%d/%m/%Y"
            )
            .strftime("%Y-%m-%d")
        )

        return f"'{data_convertida}'"

    except Exception:

        return match.group(0)


def converter_oracle_para_postgres(sql):

    sql = re.sub(
        r'VARCHAR2\s*\(',
        'VARCHAR(',
        sql,
        flags=re.IGNORECASE
    )

    sql = re.sub(
        r'\bSYSDATE\b',
        'CURRENT_DATE',
        sql,
        flags=re.IGNORECASE
    )

    sql = re.sub(
        r"TO_DATE\s*\(\s*'(\d{2}/\d{2}/\d{4})'\s*,\s*'DD/MM/YYYY'\s*\)",
        converter_to_date,
        sql,
        flags=re.IGNORECASE
    )

    return sql


def converter_arquivos():
    diretorio_projeto = Path(__file__).resolve().parent.parent
    diretorio_dados = diretorio_projeto / "data"
    arquivos = [
        diretorio_dados / "01_salvador_ddl.sql",
        diretorio_dados / "02_salvador_dml.sql"
    ]

    for arquivo in arquivos:

        try:

            conteudo = arquivo.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:

            conteudo = arquivo.read_text(
                encoding="latin-1"
            )

        resultado = converter_oracle_para_postgres(
            conteudo
        )

        novo_arquivo = arquivo.with_name(
            f"{arquivo.stem}_postgres{arquivo.suffix}"
        )

        with open(
            novo_arquivo,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(resultado)

        print(
            f"Convertido: {novo_arquivo.name}"
        )


if __name__ == "__main__":
    converter_arquivos()
