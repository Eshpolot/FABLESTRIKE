#!/usr/bin/env python3
"""Сверка звука с событиями игры.
Вход: журнал игры (строки EV/SND с метками времени, ключ --sndtest), запись общей шины sndtest.wav, папка исходных звуков.
Для каждого вызова звука в записи ищется место, где он действительно зазвучал (корреляция огибающих с исходным файлом),
и печатается задержка от события до звука в мс."""
import sys, re, wave, glob, os, numpy as np
log, wavp, snd = sys.argv[1], sys.argv[2], sys.argv[3]

def read(p):
    w = wave.open(p); sr = w.getframerate(); ch = w.getnchannels(); sw = w.getsampwidth()
    d = np.frombuffer(w.readframes(w.getnframes()), dtype={2: np.int16, 4: np.int32}[sw]).astype(float).reshape(-1, ch).mean(1)
    return sr, d / float(2 ** (8 * sw - 1))

def env(d, sr):
    hop = sr // 1000
    n = len(d) // hop
    return np.abs(d[:n * hop]).reshape(n, hop).max(1)

ev = []
for l in open(log, encoding='utf-8', errors='replace'):
    m = re.match(r'(EV|SND) (\d+) (.+)', l.strip())
    if m:
        ev.append((m.group(1), int(m.group(2)), m.group(3)))
t0 = [t for k, t, n in ev if n == 'rec_start'][0]
sr, d = read(wavp)
E = env(d, sr)
src = {}
def variants(n):
    if n not in src:
        fs = [f for f in glob.glob(os.path.join(snd, n + '*.wav')) if re.fullmatch(re.escape(n) + r'_?\d*\.wav', os.path.basename(f))]
        src[n] = [env(*read(f)[::-1]) for f in fs]
    return src[n]
rows = []
for k, t, n in ev:
    if k != 'SND':
        continue
    tr = t - t0
    best = (None, -1.0)
    for e in variants(n):
        L = min(len(e), 140)
        ref = e[:L] - e[:L].mean()
        for lag in range(-25, 180):
            a = tr + lag
            if a < 0 or a + L > len(E):
                continue
            seg = E[a:a + L] - E[a:a + L].mean()
            c = float(np.dot(ref, seg) / (np.linalg.norm(ref) * np.linalg.norm(seg) + 1e-9))
            if c > best[1]:
                best = (lag, c)
    rows.append((n, tr, best[0], best[1]))
print('запись %.2f с, вызовов звука: %d' % (len(d) / sr, len(rows)))
ok = [r for r in rows if r[2] is not None and r[3] > 0.5]
for n, t, lag, c in rows:
    print('  %-10s t=%6d мс  звук через %s' % (n, t, ('%+4d мс (совпадение %.2f)' % (lag, c)) if lag is not None and c > 0.5 else 'не найден'))
lags = [r[2] for r in ok]
print('найдено %d из %d; задержка: средняя %.0f мс, максимум %d мс' % (len(ok), len(rows), np.mean(lags), max(lags)))
pairs = []
for i, (k, t, n) in enumerate(ev):
    if k == 'EV' and (n.startswith('shot_') or n.startswith('anim_') or n.startswith('step')):
        nxt = [x for x in ev[i + 1:i + 3] if x[0] == 'SND']
        if nxt:
            pairs.append(nxt[0][1] - t)
print('событие игры -> вызов звука: максимум %d мс по %d событиям' % (max(pairs), len(pairs)))
