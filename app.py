from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, flash, redirect, render_template, request, send_file, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "radar_full_gutos.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = "radar-full-gutos-car"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c[1] == column for c in cols)


def init_db() -> None:
    """Garante que o banco tenha os campos necessários para novos anúncios e ausentes."""
    with get_conn() as conn:
        # Migrações leves para bancos antigos já criados.
        if not column_exists(conn, "anuncios_full", "ativo_no_relatorio"):
            conn.execute("ALTER TABLE anuncios_full ADD COLUMN ativo_no_relatorio TEXT NOT NULL DEFAULT 'SIM'")
        if not column_exists(conn, "anuncios_full", "data_ultima_importacao"):
            conn.execute("ALTER TABLE anuncios_full ADD COLUMN data_ultima_importacao TEXT")
        if not column_exists(conn, "anuncios_full", "data_primeira_importacao"):
            conn.execute("ALTER TABLE anuncios_full ADD COLUMN data_primeira_importacao TEXT")
        if not column_exists(conn, "anuncios_full", "observacao"):
            conn.execute("ALTER TABLE anuncios_full ADD COLUMN observacao TEXT")

        # Evita duplicidade por código de anúncio nas próximas importações.
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_anuncios_full_codigo ON anuncios_full(codigo_anuncio)"
        )
        conn.commit()


def int_safe(value: Any, default: int = 0) -> int:
    if pd.isna(value):
        return default
    try:
        text = str(value).strip()
        if text in {"", "-"}:
            return default
        return int(float(text.replace(",", ".")))
    except Exception:
        return default


def float_safe(value: Any, default: float = 0.0) -> float:
    if pd.isna(value):
        return default

    # Quando o pandas lê o Excel, PRICE geralmente já vem como número,
    # por exemplo 129.99. Nesse caso NÃO podemos remover o ponto,
    # senão 129.99 vira 12999.
    if isinstance(value, (int, float)):
        return float(value)

    try:
        text = str(value).strip()
        if text in {"", "-"}:
            return default

        text = text.replace("R$", "").strip()

        # Formato brasileiro: 1.299,99 -> 1299.99
        if "," in text:
            text = text.replace(".", "").replace(",", ".")

        # Formato americano/Excel: 129.99 -> 129.99
        return float(text)
    except Exception:
        return default


def get_series(df: pd.DataFrame, column: str, default: Any = "") -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series([default] * len(df), index=df.index)


def read_report(path: Path) -> pd.DataFrame:
    """Lê o relatório de anúncios ativos do Mercado Livre na aba Anúncios."""
    df = pd.read_excel(path, sheet_name="Anúncios", header=0, skiprows=[1, 2, 3, 4])
    df = df.dropna(how="all")

    required = ["ITEM_ID", "TITLE", "QUANTITY"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias não encontradas: {missing}")

    out = pd.DataFrame()
    out["codigo_anuncio"] = df["ITEM_ID"].fillna("").astype(str).str.strip()
    out["numero_produto"] = get_series(df, "PRODUCT_NUMBER", "").fillna("").astype(str).str.strip()
    out["titulo"] = df["TITLE"].fillna("").astype(str).str.strip()
    out["variacoes"] = get_series(df, "VARIATIONS", "").fillna("").astype(str).str.strip()
    out["quantidade_full"] = df["QUANTITY"].apply(int_safe)
    out["preco"] = get_series(df, "PRICE", 0).apply(float_safe)
    out["moeda"] = get_series(df, "CURRENCY_ID", "").fillna("").astype(str).str.strip()
    out["condicao"] = get_series(df, "CONDITION", "").fillna("").astype(str).str.strip()
    out["forma_entrega"] = get_series(df, "SHIPPING_METHOD", "").fillna("").astype(str).str.strip()
    out["tipo_anuncio"] = get_series(df, "LISTING_TYPE", "").fillna("").astype(str).str.strip()
    out["status"] = get_series(df, "STATUS", "").fillna("").astype(str).str.strip()
    out["altura_cm"] = get_series(df, "SHIPPING_HEIGHT", 0).apply(int_safe)
    out["largura_cm"] = get_series(df, "SHIPPING_WIDTH", 0).apply(int_safe)
    out["profundidade_cm"] = get_series(df, "SHIPPING_DEPTH", 0).apply(int_safe)
    out["peso_kg"] = get_series(df, "SHIPPING_WEIGHT", 0).apply(float_safe)

    out = out[out["codigo_anuncio"].str.startswith("MLB")].copy()
    out = out.drop_duplicates(subset=["codigo_anuncio"], keep="last")
    return out


@app.route("/")
def index():
    init_db()
    busca = request.args.get("busca", "").strip()
    filtro = request.args.get("filtro", "ativos")

    where = []
    params: list[Any] = []

    if busca:
        where.append("(codigo_anuncio LIKE ? OR numero_produto LIKE ? OR titulo LIKE ?)")
        termo = f"%{busca}%"
        params.extend([termo, termo, termo])

    if filtro == "ativos":
        where.append("ativo_no_relatorio = 'SIM'")
    elif filtro == "inativos":
        where.append("ativo_no_relatorio = 'NAO'")
    elif filtro == "repor":
        where.append("ativo_no_relatorio = 'SIM' AND precisa_repor = 'SIM'")
    elif filtro == "enviar":
        where.append("ativo_no_relatorio = 'SIM' AND quantidade_enviar_full > 0")
    elif filtro == "sem_config":
        where.append("ativo_no_relatorio = 'SIM' AND estoque_minimo = 0 AND estoque_recomendado = 0")
    elif filtro == "novos":
        where.append("ativo_no_relatorio = 'SIM' AND estoque_minimo = 0 AND estoque_recomendado = 0")

    sql = "SELECT * FROM anuncios_full"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY ativo_no_relatorio DESC, quantidade_enviar_full DESC, titulo ASC"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        metrics = conn.execute(
            """
            SELECT
                COUNT(*) AS total_base,
                SUM(CASE WHEN ativo_no_relatorio = 'SIM' THEN 1 ELSE 0 END) AS total_anuncios,
                SUM(CASE WHEN ativo_no_relatorio = 'NAO' THEN 1 ELSE 0 END) AS total_inativos,
                SUM(CASE WHEN ativo_no_relatorio = 'SIM' THEN quantidade_full ELSE 0 END) AS total_full,
                SUM(CASE WHEN ativo_no_relatorio = 'SIM' THEN quantidade_enviar_full ELSE 0 END) AS total_enviar,
                SUM(CASE WHEN ativo_no_relatorio = 'SIM' AND precisa_repor = 'SIM' THEN 1 ELSE 0 END) AS qtd_repor,
                SUM(CASE WHEN ativo_no_relatorio = 'SIM' AND estoque_minimo = 0 AND estoque_recomendado = 0 THEN 1 ELSE 0 END) AS sem_config
            FROM anuncios_full
            """
        ).fetchone()

    return render_template("index.html", rows=rows, metrics=metrics, busca=busca, filtro=filtro)


@app.route("/produto/<int:produto_id>", methods=["GET", "POST"])
def produto(produto_id: int):
    init_db()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM anuncios_full WHERE id = ?", (produto_id,)).fetchone()
        if row is None:
            flash("Produto não encontrado.", "danger")
            return redirect(url_for("index"))

        if request.method == "POST":
            estoque_minimo = int_safe(request.form.get("estoque_minimo"), 0)
            estoque_recomendado = int_safe(request.form.get("estoque_recomendado"), 0)
            observacao = request.form.get("observacao", "").strip()
            conn.execute(
                """
                UPDATE anuncios_full
                SET estoque_minimo = ?, estoque_recomendado = ?, observacao = ?, atualizado_em = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (estoque_minimo, estoque_recomendado, observacao, produto_id),
            )
            conn.commit()
            flash("Estoque mínimo e recomendado atualizados.", "success")
            return redirect(url_for("produto", produto_id=produto_id))

    return render_template("produto.html", row=row)


@app.route("/importar", methods=["GET", "POST"])
def importar():
    init_db()
    resultado = None
    if request.method == "POST":
        file = request.files.get("arquivo")

        if not file or not file.filename:
            flash("Selecione um arquivo Excel.", "warning")
            return redirect(url_for("importar"))

        filename = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        path = UPLOAD_DIR / filename
        file.save(path)

        try:
            df_new = read_report(path)
            if df_new.empty:
                raise ValueError("Nenhum anúncio MLB encontrado na aba Anúncios.")

            backup_path = BASE_DIR / f"backup_radar_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(DB_PATH, backup_path)

            alterados = []
            novos = []
            ausentes = []
            import_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with get_conn() as conn:
                old_rows = conn.execute("SELECT * FROM anuncios_full").fetchall()
                old_by_code = {r["codigo_anuncio"]: dict(r) for r in old_rows}
                new_codes = set(df_new["codigo_anuncio"].tolist())
                old_codes = set(old_by_code.keys())

                # Primeiro marca todos como ausentes; os que vierem no relatório voltam para SIM.
                conn.execute("UPDATE anuncios_full SET ativo_no_relatorio = 'NAO', atualizado_em = CURRENT_TIMESTAMP")

                for _, r in df_new.iterrows():
                    codigo = r["codigo_anuncio"]
                    old = old_by_code.get(codigo)

                    if old:
                        changes = {}
                        for col in [
                            "numero_produto", "titulo", "variacoes", "quantidade_full", "preco", "moeda",
                            "condicao", "forma_entrega", "tipo_anuncio", "status", "altura_cm", "largura_cm",
                            "profundidade_cm", "peso_kg", "ativo_no_relatorio"
                        ]:
                            old_val = old.get(col)
                            new_val = "SIM" if col == "ativo_no_relatorio" else r[col]
                            if str(old_val) != str(new_val):
                                changes[col] = {"antes": old_val, "depois": new_val}

                        if changes:
                            alterados.append({"codigo_anuncio": codigo, "titulo": r["titulo"], "changes": changes})

                        conn.execute(
                            """
                            UPDATE anuncios_full
                            SET numero_produto=?, titulo=?, variacoes=?, quantidade_full=?, preco=?, moeda=?, condicao=?,
                                forma_entrega=?, tipo_anuncio=?, status=?, altura_cm=?, largura_cm=?, profundidade_cm=?,
                                peso_kg=?, ativo_no_relatorio='SIM', data_ultima_importacao=?, atualizado_em=CURRENT_TIMESTAMP
                            WHERE codigo_anuncio=?
                            """,
                            (
                                r["numero_produto"], r["titulo"], r["variacoes"], int(r["quantidade_full"]),
                                float(r["preco"]), r["moeda"], r["condicao"], r["forma_entrega"], r["tipo_anuncio"],
                                r["status"], int(r["altura_cm"]), int(r["largura_cm"]), int(r["profundidade_cm"]),
                                float(r["peso_kg"]), import_time, codigo,
                            ),
                        )
                    else:
                        novos.append({
                            "codigo_anuncio": codigo,
                            "titulo": r["titulo"],
                            "quantidade_full": int(r["quantidade_full"]),
                        })
                        conn.execute(
                            """
                            INSERT INTO anuncios_full (
                                codigo_anuncio, numero_produto, titulo, variacoes, quantidade_full, preco, moeda, condicao,
                                forma_entrega, tipo_anuncio, status, altura_cm, largura_cm, profundidade_cm, peso_kg,
                                estoque_minimo, estoque_recomendado, ativo_no_relatorio,
                                data_primeira_importacao, data_ultima_importacao
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 'SIM', ?, ?)
                            """,
                            (
                                codigo, r["numero_produto"], r["titulo"], r["variacoes"], int(r["quantidade_full"]),
                                float(r["preco"]), r["moeda"], r["condicao"], r["forma_entrega"], r["tipo_anuncio"],
                                r["status"], int(r["altura_cm"]), int(r["largura_cm"]), int(r["profundidade_cm"]),
                                float(r["peso_kg"]), import_time, import_time,
                            ),
                        )

                missing_codes = sorted(old_codes - new_codes)
                for code in missing_codes:
                    ausentes.append({
                        "codigo_anuncio": code,
                        "titulo": old_by_code[code].get("titulo", ""),
                        "quantidade_full": old_by_code[code].get("quantidade_full", 0),
                    })

                conn.commit()

            resultado = {
                "total_relatorio": int(len(df_new)),
                "alterados": alterados,
                "novos": novos,
                "ausentes": ausentes,
                "backup": backup_path.name,
            }
            flash("Relatório importado com sucesso. Anúncios novos foram adicionados e ausentes foram marcados como inativos.", "success")

        except Exception as e:
            flash(f"Erro ao importar relatório: {e}", "danger")

    return render_template("importar.html", resultado=resultado)


@app.route("/exportar")
def exportar():
    init_db()
    out_path = BASE_DIR / "reposicao_full.csv"
    with get_conn() as conn:
        df = pd.read_sql_query(
            """
            SELECT codigo_anuncio, numero_produto, titulo, quantidade_full, estoque_minimo,
                   estoque_recomendado, quantidade_enviar_full, precisa_repor, preco, status, forma_entrega
            FROM anuncios_full
            WHERE ativo_no_relatorio = 'SIM' AND quantidade_enviar_full > 0
            ORDER BY quantidade_enviar_full DESC, titulo ASC
            """,
            conn,
        )
    df.to_csv(out_path, index=False, sep=";", encoding="utf-8-sig")
    return send_file(out_path, as_attachment=True, download_name="reposicao_full.csv")


if __name__ == "__main__":
    import os
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
