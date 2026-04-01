"""
Extrai a tabela NCM -> MVA da Lei nº 6.108/2022 (AM) e gera src/data/ncm_data.json.

Uso:
    python scripts/extract_ncm.py

Requer:
    pip install pdfplumber
"""

import json
import re
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    sys.exit("Erro: pdfplumber não instalado. Execute: pip install pdfplumber")

PDF_PATH = Path(__file__).parent.parent / "assets" / "LEI Nº 6.108_22.pdf"
OUTPUT_PATH = Path(__file__).parent.parent / "src" / "data" / "ncm_data.json"

# Regex para validar código NCM: apenas dígitos e pontos
NCM_PATTERN = re.compile(r"^[\d.]+$")

# Regex para extrair valor numérico de percentual (ex: "71,78%", "27%", "36,56%")
MVA_PATTERN = re.compile(r"(\d+[,.]?\d*)")


def parse_mva(value: str) -> str | None:
    """Extrai o valor numérico do MVA como string (ex: '71.78', '27')."""
    if not value:
        return None
    value = str(value).strip()
    match = MVA_PATTERN.search(value)
    if match:
        return match.group(1).replace(",", ".")
    return None


def split_ncms(cell: str) -> list[str]:
    """Uma célula pode conter múltiplos NCMs separados por newline."""
    return [p.strip() for p in str(cell).split("\n") if p.strip()]


def clean_text(text: str) -> str:
    """Remove quebras de linha internas de descrições."""
    if not text:
        return ""
    return " ".join(str(text).split())


def extract_entries(pdf_path: Path) -> list[dict]:
    entries = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row:
                        continue

                    ncm_raw = None
                    mva_raw = None
                    desc_raw = None

                    num_cols = len(row)

                    if num_cols == 4:
                        # Anexo I: ITEM | DESCRIÇÃO | NCM | % AGREGADO
                        ncm_raw = row[2]
                        desc_raw = row[1]
                        mva_raw = row[3]

                    elif num_cols == 5:
                        # Demais Anexos: ITEM | CEST | NCM | DESCRIÇÃO | MVA
                        ncm_raw = row[2]
                        desc_raw = row[3]
                        mva_raw = row[4]

                    elif num_cols == 6:
                        # Autopecas (Anexo III): ITEM | CEST | NCM | DESCRIÇÃO | MVA_COM | MVA_SEM
                        # Usa MVA SEM índice/contrato de fidelidade (col 5)
                        ncm_raw = row[2]
                        desc_raw = row[3]
                        mva_raw = row[5]

                    else:
                        continue

                    mva = parse_mva(mva_raw)
                    if not mva or not ncm_raw:
                        continue

                    descricao = clean_text(desc_raw)

                    for ncm in split_ncms(ncm_raw):
                        ncm_clean = ncm.strip().replace(" ", "")
                        if NCM_PATTERN.match(ncm_clean):
                            entries.append({
                                "ncm": ncm_clean,
                                "mva": mva,
                                "descricao": descricao,
                            })

    return entries


def deduplicate(entries: list[dict]) -> list[dict]:
    """
    Remove duplicatas mantendo a entrada mais específica (NCM mais longo)
    quando há conflito no mesmo código normalizado.
    """
    seen: dict[str, dict] = {}
    for entry in entries:
        key = re.sub(r"\D", "", entry["ncm"])  # somente dígitos
        if key not in seen or len(entry["ncm"]) > len(seen[key]["ncm"]):
            seen[key] = entry
    return list(seen.values())


def main():
    if not PDF_PATH.exists():
        sys.exit(f"PDF não encontrado em: {PDF_PATH}")

    print(f"Lendo: {PDF_PATH}")
    entries = extract_entries(PDF_PATH)
    print(f"  Entradas brutas extraídas: {len(entries)}")

    entries = deduplicate(entries)
    print(f"  Entradas após deduplicação: {len(entries)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"  Salvo em: {OUTPUT_PATH}")

    # Validação rápida dos exemplos do usuário
    key_map = {re.sub(r"\D", "", e["ncm"]): e for e in entries}

    def lookup(ncm_input: str) -> dict | None:
        digits = re.sub(r"\D", "", ncm_input)
        for length in range(len(digits), 0, -1):
            prefix = digits[:length]
            if prefix in key_map:
                return key_map[prefix]
        return None

    print("\nValidação dos exemplos:")
    tests = [
        ("8471.30.12", "27"),
        ("3916.90.10", "70"),
        ("8716.90.90", "71.78"),
        ("3822.90.00", None),
    ]
    all_ok = True
    for ncm, expected_mva in tests:
        result = lookup(ncm)
        got = result["mva"] if result else None
        ok = got == expected_mva
        status = "OK" if ok else "FALHOU"
        matched = result["ncm"] if result else "não encontrado"
        print(f"  [{status}] {ncm} -> MVA={got} (matched: {matched}, esperado: {expected_mva})")
        if not ok:
            all_ok = False

    if all_ok:
        print("\nTodos os exemplos validados com sucesso!")
    else:
        print("\nAtenção: alguns exemplos falharam.")


if __name__ == "__main__":
    main()
