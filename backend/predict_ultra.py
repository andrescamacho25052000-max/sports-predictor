import sys, io, math, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

XG_MX = 1.65
XG_SA = 0.90
XG_TOTAL = XG_MX + XG_SA
INT_FACTOR = 0.65

mx_players = [
    ("Santiago Gimenez",    0.500, 0.104, "API-Sports real",    "CF titular"),
    ("Raul Jimenez",        0.324, 0.054, "Sporting KC 2024",   "CF rotacion"),
    ("Roberto Alvarado",    0.262, 0.214, "API-Sports real",    "Extremo/10"),
    ("Cesar Huerta",        0.220, 0.085, "Pumas 2024 est.",    "Extremo"),
    ("Julian Quinones",     0.180, 0.090, "America 2024 est.",  "Extremo"),
    ("Alvaro Fidalgo",      0.145, 0.145, "API-Sports real",    "MCO"),
    ("Luis Chavez",         0.060, 0.090, "Pachuca est.",       "MCO/FK"),
    ("Orbelin Pineda",      0.041, 0.041, "API-Sports real",    "MC"),
    ("Edson Alvarez",       0.000, 0.026, "API-Sports real",    "MCD"),
]

sa_players = [
    ("Evidence Makgopa",    0.185, 0.040, "Sundowns 2024 est.", "CF titular"),
    ("Lyle Foster",         0.132, 0.151, "API-Sports real",    "CF/EXT"),
    ("Oswin Appollis",      0.172, 0.062, "API-Sports real",    "Extremo"),
    ("Relebohile Mofokeng", 0.155, 0.080, "Sundowns 2024 est.", "Extremo"),
    ("Themba Zwane",        0.167, 0.083, "API-Sports real",    "MC ofensivo"),
    ("Teboho Mokoena",      0.025, 0.125, "API-Sports real",    "MC creador"),
    ("Iqraam Rayners",      0.180, 0.060, "API-Sports real",    "CF suplente"),
]

def poisson_prob(lam, k):
    return (lam**k * math.exp(-lam)) / math.factorial(k)

def over_prob(lam, threshold):
    total = sum(poisson_prob(lam, k) for k in range(int(threshold) + 1))
    return round((1 - total) * 100, 1)

def at_least_one(lam):
    return round((1 - math.exp(-lam)) * 100, 1)

ou = {}
for t in [0.5, 1.5, 2.5, 3.5, 4.5]:
    key = str(t).replace('.', '')
    ou[f"over_{t}"]  = over_prob(XG_TOTAL, t - 0.5)
    ou[f"under_{t}"] = round(100 - ou[f"over_{t}"], 1)

mx_score = at_least_one(XG_MX)
sa_score = at_least_one(XG_SA)
btts     = round(mx_score/100 * sa_score/100 * 100, 1)
cs_sa    = round((1 - mx_score/100) * 100, 1)
cs_mx    = round((1 - sa_score/100) * 100, 1)

HT = 0.38
XG_MX_1H = round(XG_MX * HT, 3)
XG_SA_1H = round(XG_SA * HT, 3)
XG_MX_2H = round(XG_MX * (1-HT), 3)
XG_SA_2H = round(XG_SA * (1-HT), 3)
XG_1H    = round(XG_MX_1H + XG_SA_1H, 3)
XG_2H    = round(XG_MX_2H + XG_SA_2H, 3)

half = {
    "ht_over05":   at_least_one(XG_1H),
    "ht_over15":   over_prob(XG_1H, 0.5),
    "ht_under05":  0,
    "ht_under15":  0,
    "mx_ht_score": at_least_one(XG_MX_1H),
    "sa_ht_score": at_least_one(XG_SA_1H),
    "sh_over05":   at_least_one(XG_2H),
    "sh_over15":   over_prob(XG_2H, 0.5),
    "mx_sh_score": at_least_one(XG_MX_2H),
    "sa_sh_score": at_least_one(XG_SA_2H),
}
half["ht_under05"] = round(100 - half["ht_over05"], 1)
half["ht_under15"] = round(100 - half["ht_over15"], 1)

YEL_MX = 1.85; YEL_SA = 2.10; YEL_TOT = round(YEL_MX + YEL_SA, 2)
cards = {
    "yel_mx": YEL_MX, "yel_sa": YEL_SA, "yel_tot": YEL_TOT,
    "over35": over_prob(YEL_TOT, 2.5), "under35": 0,
    "over45": over_prob(YEL_TOT, 3.5), "under45": 0,
    "red_prob_mx": round((1 - math.exp(-0.12)) * 100, 1),
    "red_prob_sa": round((1 - math.exp(-0.18)) * 100, 1),
}
cards["under35"] = round(100 - cards["over35"], 1)
cards["under45"] = round(100 - cards["over45"], 1)

COR_MX = 5.23; COR_SA = 3.86; COR_TOT = round(COR_MX + COR_SA, 2)
corners = {
    "mx": COR_MX, "sa": COR_SA, "total": COR_TOT,
    "over85":  over_prob(COR_TOT, 7.5),
    "over95":  over_prob(COR_TOT, 8.5),
    "over105": over_prob(COR_TOT, 9.5),
    "over115": over_prob(COR_TOT, 10.5),
    "under85": 0, "under95": 0, "under105": 0,
}
for k in ["85","95","105"]:
    corners[f"under{k}"] = round(100 - corners[f"over{k}"], 1)

def player_score(gpg, team_xg, pool):
    gpg_i = gpg * INT_FACTOR
    share = gpg_i / pool if pool else 0
    pxg   = share * team_xg
    return round((1 - math.exp(-pxg)) * 100, 1), round(pxg, 3)

def player_assist(apg, team_xg, pool):
    apg_i = apg * INT_FACTOR
    share = apg_i / pool if pool else 0
    pxg   = share * team_xg
    return round((1 - math.exp(-pxg)) * 100, 1)

mx_pool   = sum(p[1]*INT_FACTOR for p in mx_players if p[1] > 0)
sa_pool   = sum(p[1]*INT_FACTOR for p in sa_players if p[1] > 0)
mx_pool_a = sum(p[2]*INT_FACTOR for p in mx_players if p[2] > 0)
sa_pool_a = sum(p[2]*INT_FACTOR for p in sa_players if p[2] > 0)

scorers_mx = sorted(
    [(n, *player_score(g,XG_MX,mx_pool), a, s, r) for n,g,a,s,r in mx_players if g>0],
    key=lambda x: -x[1]
)
scorers_sa = sorted(
    [(n, *player_score(g,XG_SA,sa_pool), a, s, r) for n,g,a,s,r in sa_players if g>0],
    key=lambda x: -x[1]
)
assists_mx = sorted(
    [(n, player_assist(a,XG_MX,mx_pool_a), s, r) for n,g,a,s,r in mx_players if a>0],
    key=lambda x: -x[1]
)
assists_sa = sorted(
    [(n, player_assist(a,XG_SA,sa_pool_a), s, r) for n,g,a,s,r in sa_players if a>0],
    key=lambda x: -x[1]
)

result = {
    "xg":  {"mx": XG_MX, "sa": XG_SA, "total": XG_TOTAL},
    "half_xg": {
        "1h": {"mx": XG_MX_1H, "sa": XG_SA_1H, "total": XG_1H},
        "2h": {"mx": XG_MX_2H, "sa": XG_SA_2H, "total": XG_2H},
    },
    "ou": ou,
    "half": half,
    "btts": btts, "mx_score": mx_score, "sa_score": sa_score,
    "cs_mx": cs_mx, "cs_sa": cs_sa,
    "cards": cards,
    "fouls": {"mx": 14.41, "sa": 15.85, "total": 30.26},
    "corners": corners,
    "scorers_mx": [[n,p,pxg,s,r] for n,p,pxg,a,s,r in scorers_mx[:6]],
    "scorers_sa": [[n,p,pxg,s,r] for n,p,pxg,a,s,r in scorers_sa[:5]],
    "assists_mx": [[n,p,s,r] for n,p,s,r in assists_mx[:5]],
    "assists_sa": [[n,p,s,r] for n,p,s,r in assists_sa[:5]],
}
print(json.dumps(result, ensure_ascii=False, indent=2))
