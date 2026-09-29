# Betik çıktısı: rapor tabloları

Bu dosya `analysis/analyze.py` tarafından üretilir; elle düzenlenmez.

## Özet tablo (ms)

| Senaryo | Kabul edilen olay | Başarılı (ok) | R min | R ort | R medyan | R p95 | R maks (gözlenen) | > 20 ms | drop | tx_error | timeout | Kayıt kaybı |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S0 | 35 | 35 | 5,675 | 5,676 | 5,676 | 5,679 | 5,680 | 0 | 0 | 0 | 0 | 0 |
| S1 | 30 | 30 | 5,675 | 5,837 | 5,676 | 7,783 | 8,325 | 0 | 0 | 0 | 0 | 0 |
| S2 | 30 | 30 | 5,675 | 6,102 | 5,676 | 10,333 | 10,730 | 0 | 0 | 0 | 0 | 0 |
| S3 | 30 | 30 | 5,675 | 7,114 | 6,639 | 9,958 | 10,662 | 0 | 0 | 0 | 0 | 0 |
| S4 | 32 | 32 | 5,675 | 8,178 | 7,350 | 12,773 | 13,011 | 0 | 0 | 0 | 0 | 0 |
| S5 | 30 | 28 | 19,240 | 121,767 | 151,999 | 164,969 | 164,997 | 27 | 2 | 0 | 0 | 0 |

## Aşama süreleri (ms, başarılı olayların ortalaması)

| Senaryo | t₁ − t₀ | t₂ − t₁ | t₃ − t₂ | t₄ − t₃ | R |
|---|---|---|---|---|---|
| S0 | 0,024 | 0,037 | 0,056 | 5,559 | 5,676 |
| S1 | 0,025 | 0,037 | 0,215 | 5,559 | 5,837 |
| S2 | 0,024 | 0,037 | 0,481 | 5,559 | 6,102 |
| S3 | 0,024 | 0,039 | 1,492 | 5,559 | 7,114 |
| S4 | 0,167 | 0,038 | 2,414 | 5,559 | 8,178 |
| S5 | 0,698 | 0,038 | 115,472 | 5,559 | 121,767 |

## Kart sayaçları

| Senaryo | tx_drop_tel | bounce_rejected | periyot min/maks (µs) | CPU işi min/maks (µs) |
|---|---|---|---|---|
| S0 | 0 | 0 | — | — |
| S1 | 0 | 0 | 100000 / 100000 | — |
| S2 | 0 | 0 | 19997 / 20003 | — |
| S3 | 0 | 0 | 9997 / 10003 | — |
| S4 | 0 | 0 | 9997 / 10003 | 2002 / 2064 |
| S5 | 14 | 0 | 9998 / 10003 | 5002 / 5090 |

## Ek gözlemler

| Senaryo | Hat doluluğu (%) | t₃ − t₂ > 1 ms olan olay | t₃ faz bandı (t₃ mod periyot, µs) |
|---|---|---|---|
| S1 | 5.6 | 2 / 30 | 2354–99842 |
| S2 | 27.8 | 4 / 30 | 683–19702 |
| S3 | 55.6 | 15 / 30 | 4740–8361 |
| S4 | 55.6 | 19 / 32 | 6743–8820 |
| S5 | 55.6 | 28 / 28 | 7183–7190 |

S5 plato: olay ≥ 15 için R ort = 163,064 ms (n = 14). Kuyruk uzunluğu × periyot = 16 × 10 ms = 160 ms.

## Dışlanan kayıtlar

Zaman istatistiklerinden dışlandı; özet tablodaki olay sayılarında ve kayıp sütunlarında yer alır.

| Senaryo | Olay | Durum | Neden |
|---|---|---|---|
| S5 | 17 | tx_drop | eksik: t3,t4 |
| S5 | 28 | tx_drop | eksik: t3,t4 |
