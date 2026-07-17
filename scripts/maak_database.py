from pathlib import Path
import sqlite3
import sys

import pandas as pd


# --------------------------------------------------
# Mappen en bestanden
# --------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
BRONDATA_DIR = PROJECT_DIR / "brondata"

CONTROL_FILE = BRONDATA_DIR / "Control overzicht 20260717.xlsx"
RISK_FILE = BRONDATA_DIR / "Risk overzicht 20260717.xlsx"

DATABASE_FILE = PROJECT_DIR / "grc_audit.db"
TEMP_DATABASE_FILE = PROJECT_DIR / "grc_audit_new.db"


# --------------------------------------------------
# Hulpfuncties
# --------------------------------------------------

def controleer_bestand(bestand: Path) -> None:
    if not bestand.exists():
        raise FileNotFoundError(
            f"Bestand niet gevonden:\n{bestand}"
        )


def lees_controls() -> pd.DataFrame:
    # Leest altijd het eerste werkblad
    dataframe = pd.read_excel(
        CONTROL_FILE,
        sheet_name=0
    )

    dataframe.columns = [
        str(kolom).strip()
        for kolom in dataframe.columns
    ]

    vereiste_kolommen = [
        "Control Identifier",
        "Control Description"
    ]

    ontbrekend = [
        kolom
        for kolom in vereiste_kolommen
        if kolom not in dataframe.columns
    ]

    if ontbrekend:
        raise ValueError(
            "Ontbrekende kolommen in controlbestand: "
            + ", ".join(ontbrekend)
            + "\nAanwezige kolommen: "
            + ", ".join(map(str, dataframe.columns))
        )

    dataframe = dataframe[
        ["Control Identifier", "Control Description"]
    ].copy()

    dataframe.columns = [
        "control_id",
        "description"
    ]

    return valideer_data(
        dataframe=dataframe,
        id_kolom="control_id",
        soort="control"
    )


def lees_risicos() -> pd.DataFrame:
    # Leest altijd het eerste werkblad
    dataframe = pd.read_excel(
        RISK_FILE,
        sheet_name=0
    )

    dataframe.columns = [
        str(kolom).strip()
        for kolom in dataframe.columns
    ]

    vereiste_kolommen = [
        "Riks Identifier",
        "Risk Description"
    ]

    ontbrekend = [
        kolom
        for kolom in vereiste_kolommen
        if kolom not in dataframe.columns
    ]

    if ontbrekend:
        raise ValueError(
            "Ontbrekende kolommen in risicobestand: "
            + ", ".join(ontbrekend)
            + "\nAanwezige kolommen: "
            + ", ".join(map(str, dataframe.columns))
        )

    dataframe = dataframe[
        ["Riks Identifier", "Risk Description"]
    ].copy()

    dataframe.columns = [
        "risk_id",
        "description"
    ]

    return valideer_data(
        dataframe=dataframe,
        id_kolom="risk_id",
        soort="risico"
    )


def valideer_data(
    dataframe: pd.DataFrame,
    id_kolom: str,
    soort: str
) -> pd.DataFrame:
    dataframe = dataframe.dropna(how="all").copy()

    if dataframe[id_kolom].isna().any():
        raise ValueError(
            f"Er zijn lege {soort}-ID's gevonden."
        )

    if dataframe["description"].isna().any():
        raise ValueError(
            f"Er zijn lege {soort}beschrijvingen gevonden."
        )

    dataframe[id_kolom] = pd.to_numeric(
        dataframe[id_kolom],
        errors="raise"
    ).astype(int)

    dataframe["description"] = (
        dataframe["description"]
        .astype(str)
        .str.strip()
    )

    lege_beschrijvingen = dataframe["description"].eq("")

    if lege_beschrijvingen.any():
        ids = dataframe.loc[
            lege_beschrijvingen,
            id_kolom
        ].tolist()

        raise ValueError(
            f"Lege beschrijving voor {soort}-ID(s): {ids}"
        )

    dubbele_ids = dataframe.loc[
        dataframe[id_kolom].duplicated(keep=False),
        id_kolom
    ].tolist()

    if dubbele_ids:
        raise ValueError(
            f"Dubbele {soort}-ID(s): "
            f"{sorted(set(dubbele_ids))}"
        )

    return dataframe.sort_values(
        id_kolom
    ).reset_index(drop=True)


def maak_database(
    controls: pd.DataFrame,
    risicos: pd.DataFrame
) -> None:
    if TEMP_DATABASE_FILE.exists():
        TEMP_DATABASE_FILE.unlink()

    verbinding = sqlite3.connect(
        TEMP_DATABASE_FILE
    )

    try:
        cursor = verbinding.cursor()

        cursor.execute("""
            CREATE TABLE controls (
                control_id INTEGER PRIMARY KEY,
                description TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE risks (
                risk_id INTEGER PRIMARY KEY,
                description TEXT NOT NULL
            )
        """)

        cursor.executemany(
            """
            INSERT INTO controls (
                control_id,
                description
            )
            VALUES (?, ?)
            """,
            controls[
                ["control_id", "description"]
            ].itertuples(
                index=False,
                name=None
            )
        )

        cursor.executemany(
            """
            INSERT INTO risks (
                risk_id,
                description
            )
            VALUES (?, ?)
            """,
            risicos[
                ["risk_id", "description"]
            ].itertuples(
                index=False,
                name=None
            )
        )

        verbinding.commit()

        aantal_controls = cursor.execute(
            "SELECT COUNT(*) FROM controls"
        ).fetchone()[0]

        aantal_risicos = cursor.execute(
            "SELECT COUNT(*) FROM risks"
        ).fetchone()[0]

        integriteit = cursor.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integriteit != "ok":
            raise RuntimeError(
                "Database-integriteitscontrole mislukt: "
                + integriteit
            )

        if aantal_controls != len(controls):
            raise RuntimeError(
                "Aantal controls in database klopt niet."
            )

        if aantal_risicos != len(risicos):
            raise RuntimeError(
                "Aantal risico's in database klopt niet."
            )

    finally:
        verbinding.close()

    # Vervangt de bestaande database pas nadat alles goed is gegaan
    TEMP_DATABASE_FILE.replace(
        DATABASE_FILE
    )

    print()
    print("========================================")
    print("DATABASE SUCCESVOL AANGEMAAKT")
    print("========================================")
    print(f"Aantal controls : {len(controls)}")
    print(f"Aantal risico's : {len(risicos)}")
    print(f"Database        : {DATABASE_FILE}")
    print("Integriteitscheck: OK")
    print("========================================")


def main() -> None:
    controleer_bestand(CONTROL_FILE)
    controleer_bestand(RISK_FILE)

    controls = lees_controls()
    risicos = lees_risicos()

    maak_database(
        controls=controls,
        risicos=risicos
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as fout:
        print()
        print("========================================")
        print("FOUT BIJ AANMAKEN DATABASE")
        print("========================================")
        print(fout)
        print("========================================")
        sys.exit(1)