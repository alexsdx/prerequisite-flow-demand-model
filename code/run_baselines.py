"""Forecasting baselines for Table 2 of the article (Section 5).

(Comments below are kept in Spanish, the working language of the authors.)

Compara el modelo de flujo de prerequisitos (Algorithm 1) contra baselines
triviales, usando EXACTAMENTE los mismos datos anonimizados y el mismo
protocolo de evaluación del repo de reproducibilidad (run_experiments.py).

Baselines (todos son pronósticos one-step-ahead de n_c(t+1)):
  PERS   Persistencia:            n_c(t)
  LY     Mismo semestre año ant.: n_c(t-1)              (t-1 = dos semestres atrás)
  LYADJ  Heurística administrador: n_c(t-1) * N(t)/N(t-2) (año anterior ajustado por tendencia global)
  HMEAN  Media histórica:         mean_{s<=t} n_c(s)
  PMEAN  Media misma paridad:     mean de semestres con la misma paridad que t+1
  SNAIVE Structural naive:        Algorithm 1 con f = 0 (aísla el término de recursadores)
  MODEL  Algorithm 1 completo (Exp 1 con reprobados observados; Exp 2 con f=0)
  HYBRID MODEL donde el prerequisito se ofertó en t; PMEAN en las demás materias

Conjuntos de evaluación:
  V*     las 34 / 12 materias validadas del artículo (comparación justa, mismo set)
  ALL    todas las materias con n>0 en t+1 y al menos un dato histórico
         (muestra el alcance de cada predictor; el modelo no cubre todo)

Salidas: consola + Baselines_Comparison.xlsx (hojas: resumen, por-materia Exp1, Exp2).
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from statistics import mean, median

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO
sys.path.insert(0, str(REPO / "code"))
from algorithm1 import compute_prerequisite_flow_demand  # noqa: E402

SEM = ["S1", "S2", "S3", "S4", "S5", "S6"]
LABEL = {"S1": "Ago-Dic 2023", "S2": "Ene-Jun 2024", "S3": "Ago-Dic 2024",
         "S4": "Ene-Jun 2025", "S5": "Ago-Dic 2025", "S6": "Ene-Jun 2026"}


def load():
    enr = {}
    with (REPO / "data/enrollments_anonymized.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            enr[(r["course_id"], r["semester"])] = int(r["enrolment_n"])
    fail = {}
    with (REPO / "data/failures_S4.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fail[(r["course_id"], "S4")] = int(r["failures_f"])
    graph = json.loads((REPO / "data/prerequisite_graph.json").read_text(encoding="utf-8"))
    return enr, fail, graph


def n_of(enr, c, s):
    return enr.get((c, s), 0)


def total(enr, s):
    return sum(v for (c, ss), v in enr.items() if ss == s)


def baselines(enr, t, t1):
    """Devuelve dict nombre -> {course: pred} para todas las materias con historia."""
    it = SEM.index(t)
    hist = SEM[: it + 1]              # S1..t
    t_minus_1 = SEM[it - 1] if it >= 1 else None
    same_parity = [s for s in hist if (SEM.index(s) % 2) == (SEM.index(t1) % 2)]
    courses = {c for (c, s) in enr if s in hist}
    ratio = total(enr, t) / total(enr, SEM[it - 2]) if it >= 2 else 1.0

    out = {"PERS": {}, "LY": {}, "LYADJ": {}, "HMEAN": {}, "PMEAN": {}}
    for c in courses:
        if n_of(enr, c, t) > 0:
            out["PERS"][c] = n_of(enr, c, t)
        if t_minus_1 and n_of(enr, c, t_minus_1) > 0:
            out["LY"][c] = n_of(enr, c, t_minus_1)
            out["LYADJ"][c] = round(n_of(enr, c, t_minus_1) * ratio)
        h = [n_of(enr, c, s) for s in hist if n_of(enr, c, s) > 0]
        if h:
            out["HMEAN"][c] = round(mean(h))
        p = [n_of(enr, c, s) for s in same_parity if n_of(enr, c, s) > 0]
        if p:
            out["PMEAN"][c] = round(mean(p))
    return out, ratio


def evaluate(pred, enr, t1, subset=None):
    rows = []
    for c, d in pred.items():
        if d <= 0:
            continue
        n = n_of(enr, c, t1)
        if n <= 0:
            continue
        if subset is not None and c not in subset:
            continue
        rows.append((c, d, n))
    if not rows:
        return None
    errs = [abs(d - n) for _, d, n in rows]
    sd, sn = sum(d for _, d, _ in rows), sum(n for _, _, n in rows)
    under = sum(1 for _, d, n in rows if d < n)
    over = sum(1 for _, d, n in rows if d > n)
    exact = len(rows) - under - over
    return {
        "N": len(rows), "sum_pred": sd, "sum_obs": sn,
        "coverage": round(sd / sn * 100, 1),
        "MAE": round(mean(errs), 1), "MedAE": round(median(errs), 1),
        "RMSE": round(math.sqrt(mean(e * e for e in errs)), 1),
        "MAPE": round(mean(abs(d - n) / n for _, d, n in rows) * 100, 1),
        "under": under, "over": over, "exact": exact,
        "rows": rows,
    }


def run_experiment(name, t, t1, enr, fail, graph, use_fail):
    model = compute_prerequisite_flow_demand(graph, enr, fail if use_fail else {}, t, t1, SEM, k=1)
    snaive = compute_prerequisite_flow_demand(graph, enr, {}, t, t1, SEM, k=1)
    bl, ratio = baselines(enr, t, t1)
    # HYBRID: flujo estructural donde el prerequisito se ofertó en t; PMEAN en el resto
    hybrid = dict(bl["PMEAN"]); hybrid.update({c: d for c, d in model.items() if c in snaive})
    preds = {"MODEL": model, "SNAIVE": snaive, **bl, "HYBRID": hybrid}
    vstar = {c for c, d in model.items() if d > 0 and n_of(enr, c, t1) > 0}
    vflow = {c for c in vstar if c in snaive}          # régimen flujo(+recursadores)
    vret = vstar - vflow                                # régimen solo-recursadores
    res_v = {k: evaluate(p, enr, t1, vstar) for k, p in preds.items()}
    res_all = {k: evaluate(p, enr, t1) for k, p in preds.items()}
    res_flow = {k: evaluate(p, enr, t1, vflow) for k, p in preds.items()}
    res_ret = {k: evaluate(p, enr, t1, vret) for k, p in preds.items()}
    return preds, vstar, res_v, res_all, ratio, (vflow, res_flow), (vret, res_ret)


def print_table(title, res):
    print(f"\n{title}")
    hdr = f"{'Predictor':8} {'N':>3} {'ΣPred':>6} {'ΣObs':>6} {'Cov%':>6} {'MAE':>6} {'MedAE':>6} {'RMSE':>6} {'MAPE%':>6} {'Sub':>4} {'Sob':>4} {'Ex':>3}"
    print(hdr); print("-" * len(hdr))
    for k, r in res.items():
        if r is None:
            print(f"{k:8} (sin predicciones)"); continue
        print(f"{k:8} {r['N']:>3} {r['sum_pred']:>6} {r['sum_obs']:>6} {r['coverage']:>6} {r['MAE']:>6} "
              f"{r['MedAE']:>6} {r['RMSE']:>6} {r['MAPE']:>6} {r['under']:>4} {r['over']:>4} {r['exact']:>3}")


def main():
    enr, fail, graph = load()
    exps = [("Exp 1", "S4", "S5", True), ("Exp 2", "S5", "S6", False)]
    xlsx_summary, xlsx_detail = [], {}

    for name, t, t1, use_fail in exps:
        preds, vstar, res_v, res_all, ratio, (vflow, res_flow), (vret, res_ret) = run_experiment(name, t, t1, enr, fail, graph, use_fail)
        print("=" * 90)
        print(f"{name}: {t} ({LABEL[t]}) -> {t1} ({LABEL[t1]})   "
              f"{'con reprobados observados' if use_fail else 'f = 0'}   ratio N(t)/N(t-2) = {ratio:.4f}")
        print_table(f"[{name}] Sobre V* (las {len(vstar)} materias validadas del artículo)", res_v)
        print_table(f"[{name}] Sobre V*_flow ({len(vflow)} materias cuyo prerequisito se ofertó en {t})", res_flow)
        if vret:
            print_table(f"[{name}] Sobre V*_retake-only ({len(vret)} materias con d = r solamente)", res_ret)
        print_table(f"[{name}] Sobre TODAS las materias ofertadas en {t1} con historia", res_all)

        for scope, res in (("V*", res_v), ("V*_flow", res_flow), ("V*_retake", res_ret), ("ALL", res_all)):
            for k, r in res.items():
                if r:
                    xlsx_summary.append({"Experimento": name, "Conjunto": scope, "Predictor": k,
                                         **{kk: vv for kk, vv in r.items() if kk != "rows"}})
        # Detalle por materia (sobre ALL, con columnas por predictor)
        courses = sorted({c for (c, s) in enr if s == t1 and enr[(c, s)] > 0})
        det = []
        for c in courses:
            row = {"course_id": c, "en_V*": c in vstar,
                   "regimen": "flujo" if c in vflow else ("solo-recursadores" if c in vret else "no-predecible"),
                   "obs_n(t+1)": n_of(enr, c, t1)}
            for s in SEM[: SEM.index(t) + 1]:
                row[f"n({s})"] = n_of(enr, c, s)
            if use_fail:
                row["f(S4)"] = fail.get((c, "S4"), 0)
            for k in ("MODEL", "SNAIVE", "PERS", "LY", "LYADJ", "HMEAN", "PMEAN", "HYBRID"):
                p = preds[k].get(c)
                row[f"pred_{k}"] = p
                row[f"res_{k}"] = (p - n_of(enr, c, t1)) if p is not None else None  # pred - obs
            det.append(row)
        xlsx_detail[name] = det

    # Excel
    try:
        import pandas as pd
        with pd.ExcelWriter(ROOT / "Baselines_Comparison.xlsx") as w:
            pd.DataFrame(xlsx_summary).to_excel(w, sheet_name="Resumen", index=False)
            for name, det in xlsx_detail.items():
                pd.DataFrame(det).to_excel(w, sheet_name=f"Detalle {name}", index=False)
        print(f"\nExcel escrito: {ROOT / 'Baselines_Comparison.xlsx'}")
    except Exception as e:  # pragma: no cover
        print("No se pudo escribir Excel:", e)


if __name__ == "__main__":
    main()
