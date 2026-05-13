from fastapi import FastAPI, HTTPException, Query
import sqlite3

app = FastAPI(title="GRC Audit API")

DB_PATH = "grc_audit.db"


def query_one(sql: str, params: tuple):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql, params)
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)


def query_many(sql: str, params: tuple):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.get("/risk/{risk_id}")
def get_risk(risk_id: int):
    row = query_one(
        "SELECT risk_id, description FROM risks WHERE risk_id = ?",
        (risk_id,)
    )

    if row is None:
        raise HTTPException(status_code=404, detail="Risk not found")

    return row


@app.get("/control/{control_id}")
def get_control(control_id: int):
    row = query_one(
        "SELECT control_id, description FROM controls WHERE control_id = ?",
        (control_id,)
    )

    if row is None:
        raise HTTPException(status_code=404, detail="Control not found")

    return row


@app.get("/risks")
def get_risks(ids: str = Query(..., description="Comma-separated risk IDs")):
    risk_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]

    placeholders = ",".join(["?"] * len(risk_ids))

    rows = query_many(
        f"SELECT risk_id, description FROM risks WHERE risk_id IN ({placeholders})",
        tuple(risk_ids)
    )

    if len(rows) != len(risk_ids):
        found_ids = {row["risk_id"] for row in rows}
        missing_ids = [risk_id for risk_id in risk_ids if risk_id not in found_ids]
        raise HTTPException(status_code=404, detail={"missing_risk_ids": missing_ids})

    return rows


@app.get("/controls")
def get_controls(ids: str = Query(..., description="Comma-separated control IDs")):
    control_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]

    placeholders = ",".join(["?"] * len(control_ids))

    rows = query_many(
        f"SELECT control_id, description FROM controls WHERE control_id IN ({placeholders})",
        tuple(control_ids)
    )

    if len(rows) != len(control_ids):
        found_ids = {row["control_id"] for row in rows}
        missing_ids = [control_id for control_id in control_ids if control_id not in found_ids]
        raise HTTPException(status_code=404, detail={"missing_control_ids": missing_ids})

    return rows