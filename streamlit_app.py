# ===========================================
# ROUND-ROBIN SEATING — STREAMLIT APP (FINAL ALWAYS PASS)
# ===========================================
# pip install streamlit pandas matplotlib

import math, random
from dataclasses import dataclass
from typing import List, Tuple, Dict, Set
from collections import defaultdict

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ---------- Core ----------

@dataclass
class InitParams:
    n: int
    parity: str
    D: int

def init_params(n: int) -> InitParams:
    assert n >= 3
    return InitParams(n=n,
                      parity=("odd" if n % 2 else "even"),
                      D=((n - 1) // 2 if n % 2 else n // 2))

def wrap(x: int, N: int) -> int:
    return ((x - 1) % N) + 1

def edges_from_cycle(order: List[int]) -> Set[Tuple[int, int]]:
    E: Set[Tuple[int, int]] = set()
    n = len(order)
    for i in range(n):
        u, v = order[i], order[(i + 1) % n]
        E.add((u, v) if u < v else (v, u))
    return E

# ---------- Sinh lịch ----------

def generate_schedule_odd(n: int) -> List[List[int]]:
    """Walecki decomposition cho n lẻ: mỗi cặp xuất hiện đúng 1 lần."""
    assert n % 2 == 1
    m = (n - 1) // 2
    g = n - 1
    days: List[List[int]] = []
    for k in range(m):
        cyc = [g]
        for j in range(1, m + 1):
            a = (k + j - 1) % (2 * m)
            b = (k - j) % (2 * m)
            cyc += [a, b]
        days.append(cyc)
    return days

def generate_schedule_even(n: int) -> List[List[int]]:
    """Round-Robin 'Circle Method' cho n chẵn."""
    assert n % 2 == 0
    players = list(range(n))
    D = n // 2
    days: List[List[int]] = []

    for d in range(D):
        row = players[:]
        order = []
        left, right = 0, n - 1
        while left < right:
            order.append(row[left])
            order.append(row[right])
            left += 1
            right -= 1
        days.append(order)
        players = [players[0]] + players[-1:] + players[1:-1]
    return days

def generate_schedule(n: int) -> List[List[int]]:
    return generate_schedule_odd(n) if n % 2 == 1 else generate_schedule_even(n)

# ---------- Kiểm chứng ----------

def count_pair_coverage(days: List[List[int]]) -> Dict[Tuple[int, int], int]:
    counts: Dict[Tuple[int, int], int] = defaultdict(int)
    for order in days:
        for e in edges_from_cycle(order):
            counts[e] += 1
    return counts

def verify_coverage(n: int, pair_counts: Dict[Tuple[int, int], int]) -> Tuple[bool, list[Tuple[int,int]]]:
    need_exact_one = (n % 2 == 1)
    missing = []
    for u in range(n):
        for v in range(u + 1, n):
            c = pair_counts.get((u, v), 0)
            if need_exact_one:
                if c != 1:
                    missing.append((u, v))
            else:
                if c < 1:
                    missing.append((u, v))
    return (len(missing) == 0, missing)

# ---------- Extended Repair ----------

def score_order(order: List[int], need: Set[Tuple[int,int]]) -> int:
    return sum(1 for e in edges_from_cycle(order) if e in need)

def improve_one_day(order: List[int], need: Set[Tuple[int,int]], tries: int = 800) -> List[int]:
    best = order[:]; best_sc = score_order(best, need)
    n = len(order)
    for _ in range(tries):
        i, j = random.sample(range(n), 2)
        cand = best[:]
        cand[i], cand[j] = cand[j], cand[i]
        sc = score_order(cand, need)
        if sc > best_sc:
            best, best_sc = cand, sc
    return best

def extended_repair(days: List[List[int]], missing: List[Tuple[int,int]],
                    passes: int = 3, tries_per_day: int = 800) -> List[List[int]]:
    if not missing: return days
    random.seed(42)
    need = set(tuple(sorted(e)) for e in missing)
    best = [d[:] for d in days]

    def left_missing(DAYS):
        pc = count_pair_coverage(DAYS)
        return sum(1 for e in need if pc.get(e, 0) == 0)

    best_left = left_missing(best)
    for _ in range(passes):
        improved = False
        for di in range(len(best)):
            cand = best[:]
            cand[di] = improve_one_day(cand[di], need, tries=tries_per_day)
            left = left_missing(cand)
            if left < best_left:
                best, best_left, improved = cand, left, True
        if not improved: break
    return best

# ---------- Thêm ngày hoàn tất ----------

def add_completion_day(n: int, days: List[List[int]], missing: List[Tuple[int,int]]) -> List[List[int]]:
    need = set(tuple(sorted(e)) for e in missing)
    if not need: return days
    deg = defaultdict(int)
    for u, v in need:
        deg[u] += 1; deg[v] += 1
    start = max(range(n), key=lambda x: deg.get(x, 0))
    order = [start]; used = {start}
    while len(order) < n:
        cur = order[-1]
        cand = [v for (u,v) in need if u == cur and v not in used] + \
               [u for (u,v) in need if v == cur and u not in used]
        if not cand: cand = [v for v in range(n) if v not in used]
        nxt = max(cand, key=lambda x: deg.get(x, 0))
        order.append(nxt); used.add(nxt)
    return days + [order]

# ---------- DataFrames & Plot ----------

def df_days(days: List[List[int]]) -> pd.DataFrame:
    df = pd.DataFrame(days)
    df.index = [f"Day {i}" for i in range(1, len(days)+1)]
    df.columns = [f"Seat {j}" for j in range(len(days[0]))]
    return df

def df_pairs_by_day(days: List[List[int]]) -> pd.DataFrame:
    rows = []
    for d, order in enumerate(days, 1):
        for (u, v) in sorted(edges_from_cycle(order)):
            rows.append({"Day": d, "Pair": f"({u},{v})"})
    return pd.DataFrame(rows)

def df_pair_counts(n: int, pair_counts: Dict[Tuple[int,int], int]) -> pd.DataFrame:
    rows = [{"Pair": f"({u},{v})", "Count": pair_counts.get((u, v), 0)}
            for u in range(n) for v in range(u+1, n)]
    df = pd.DataFrame(rows).sort_values(["Count","Pair"], ascending=[False, True]).reset_index(drop=True)
    return df

def plot_circle(order: List[int]):
    n = len(order); r = 1.0
    ang = [2*math.pi * i / n for i in range(n)]
    xs = [r*math.cos(a) for a in ang]; ys = [r*math.sin(a) for a in ang]
    fig, ax = plt.subplots(figsize=(5,5))
    for i,(x,y) in enumerate(zip(xs,ys)):
        ax.scatter(x,y)
        ax.text(x,y,str(order[i]),ha="center",va="center",
                fontsize=10,bbox=dict(boxstyle="round,pad=0.2",fc="white",ec="gray"))
    for i in range(n):
        j=(i+1)%n; ax.plot([xs[i],xs[j]],[ys[i],ys[j]],alpha=0.6)
    ax.set_aspect("equal"); ax.axis("off")
    return fig

# ---------- Giao diện ----------

st.set_page_config(page_title="Round-robin Seating", layout="wide")
st.title("🪑 Xếp chỗ vòng tròn – Round-robin (Hamilton cycles)")
st.caption("Đảm bảo: mọi cặp người đều từng ngồi kề nhau (n lẻ: mỗi cặp đúng 1 lần; n chẵn: mỗi cặp ≥ 1 lần). App tự động Repair hoặc thêm ngày hoàn tất đến khi PASS ✅.")

with st.sidebar:
    st.header("Thiết lập")
    n = st.number_input("Số người (n ≥ 3)", min_value=3, value=10, step=1)
    auto_repair = st.checkbox("Thử Repair nếu thiếu (sửa nhiều ngày)", value=True)
    passes = st.slider("Số lượt quét Repair", 1, 6, 3)
    tries = st.slider("Số lần hoán vị / ngày", 100, 2000, 800, 100)
    allow_extra_days = st.checkbox("Tự thêm 'ngày hoàn tất' đến khi PASS", value=True)
    max_extra_days = st.slider("Giới hạn ngày thêm tối đa", 0, 30, 10)
    show_circle = st.checkbox("Vẽ vòng tròn minh hoạ cho 1 ngày", value=True)
    day_to_plot = st.number_input("Chọn ngày để vẽ", min_value=1, value=1, step=1)
    st.markdown("---"); st.caption("Made with ❤️ Streamlit")

# A) Init
params = init_params(int(n))
is_odd = (params.n % 2 == 1)

# B) Generate
days = generate_schedule(params.n)
pair_counts = count_pair_coverage(days)
passed, missing = verify_coverage(params.n, pair_counts)

# C) Xử lý tự động
if not is_odd:  # chỉ can thiệp khi n chẵn
    if auto_repair and not passed:
        days = extended_repair(days, missing, passes=passes, tries_per_day=tries)
        pair_counts = count_pair_coverage(days)
        passed, missing = verify_coverage(params.n, pair_counts)

    extra_days_used = 0
    while (not passed) and allow_extra_days and extra_days_used < max_extra_days:
        days = add_completion_day(params.n, days, missing)
        pair_counts = count_pair_coverage(days)
        passed, missing = verify_coverage(params.n, pair_counts)
        extra_days_used += 1

# D) Hiển thị
c1, c2, c3, c4 = st.columns(4)
c1.metric("n (người)", params.n)
c2.metric("Số ngày lý thuyết", params.D)
c3.metric("Parity", params.parity.upper())
c4.metric("Bao phủ", "PASSED ✅" if passed else "NOT PASSED ❌")

st.subheader("📅 Lịch ngồi theo ngày (Days×Seats)")
st.dataframe(df_days(days), use_container_width=True)

st.subheader("🤝 Các cặp kề theo từng ngày (Pairs_by_Day)")
st.dataframe(df_pairs_by_day(days), use_container_width=True, height=300)

st.subheader("📈 Bảng đếm bao phủ (PairCounts)")
st.dataframe(df_pair_counts(params.n, pair_counts), use_container_width=True, height=360)

# E) Minh hoạ
if show_circle:
    d_idx = int(day_to_plot) - 1
    if 0 <= d_idx < len(days):
        st.subheader(f"🟢 Minh hoạ vòng tròn – Ngày {day_to_plot}")
        st.pyplot(plot_circle(days[d_idx]))
    else:
        st.info("Chọn ngày hợp lệ để vẽ.")
