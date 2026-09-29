# Betik çıktısı: rapor tabloları

Bu dosya `analysis/analyze.py` tarafından üretilir; elle düzenlenmez.

## Özet tablo (ms)

| Senaryo | Kabul edilen olay | Başarılı (ok) | R min | R ort | R medyan | R p95 | R maks (gözlenen) | > 20 ms | drop | tx_error | timeout | Kayıt kaybı |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S0 | 37 | 37 | 5,678 | 5,679 | 5,679 | 5,683 | 5,683 | 0 | 0 | 0 | 0 | 0 |
| S1 | 33 | 33 | 5,678 | 5,944 | 5,679 | 7,891 | 9,540 | 0 | 0 | 0 | 0 | 0 |
| S2 | 34 | 34 | 5,678 | 6,927 | 5,682 | 10,410 | 10,990 | 0 | 0 | 0 | 0 | 0 |
| S3 | 31 | 31 | 5,678 | 7,052 | 6,046 | 10,509 | 11,351 | 0 | 0 | 0 | 0 | 0 |
| S4 | 33 | 33 | 5,678 | 8,657 | 8,672 | 13,235 | 13,310 | 0 | 0 | 0 | 0 | 0 |
| S5 | 38 | 26 | 16,422 | 118,704 | 139,310 | 164,276 | 165,337 | 25 | 12 | 0 | 0 | 0 |

## Aşama süreleri (ms, başarılı olayların ortalaması)

| Senaryo | t₁ − t₀ | t₂ − t₁ | t₃ − t₂ | t₄ − t₃ | R |
|---|---|---|---|---|---|
| S0 | 0,025 | 0,037 | 0,058 | 5,559 | 5,679 |
| S1 | 0,025 | 0,038 | 0,322 | 5,559 | 5,944 |
| S2 | 0,026 | 0,038 | 1,304 | 5,559 | 6,927 |
| S3 | 0,029 | 0,038 | 1,426 | 5,559 | 7,052 |
| S4 | 0,277 | 0,038 | 2,783 | 5,559 | 8,657 |
| S5 | 0,984 | 0,038 | 112,123 | 5,559 | 118,704 |

## Kart sayaçları

| Senaryo | Gerçek telemetri hızı (Hz) | periyot min/maks (µs) | CPU işi min/maks (µs) | TX kuyruğu HWM (/16) | Buton kuyruğu HWM (/8) | tx_drop_tel | bounce_rejected |
|---|---|---|---|---|---|---|---|
| S0 | kapalı | — | — | 1 | 1 | 0 | 0 |
| S1 | 10,00 | 100000 / 100000 | — | 1 | 1 | 0 | 0 |
| S2 | 50,00 | 20000 / 20000 | — | 1 | 1 | 0 | 0 |
| S3 | 100,00 | 9979 / 10021 | — | 2 | 1 | 0 | 0 |
| S4 | 100,00 | 9996 / 10004 | 2002 / 2063 | 2 | 1 | 0 | 0 |
| S5 | 99,99 | 9998 / 10004 | 5002 / 5088 | 16 | 1 | 12 | 0 |

## Prosedür kontrolü (basış aralıkları, kartın t₀ damgalarından)

| Senaryo | Kabul edilen olay | Basış aralığı min (s) | medyan (s) | 0,5 s'den kısa |
|---|---|---|---|---|
| S0 | 37 | 0,581 | 0,779 | 0 |
| S1 | 33 | 0,501 | 0,751 | 0 |
| S2 | 34 | 0,697 | 0,827 | 0 |
| S3 | 31 | 0,677 | 0,741 | 0 |
| S4 | 33 | 0,527 | 0,605 | 0 |
| S5 | 38 | 0,544 | 0,747 | 0 |

## Ek gözlemler

| Senaryo | Hat doluluğu (%) | t₃ − t₂ > 1 ms olan olay | t₃ faz bandı (t₃ mod periyot, µs) |
|---|---|---|---|
| S1 | 5.6 | 3 / 33 | 6853–98480 |
| S2 | 27.8 | 11 / 34 | 382–19637 |
| S3 | 55.6 | 11 / 31 | 238–9829 |
| S4 | 55.6 | 23 / 33 | 7744–9980 |
| S5 | 55.6 | 26 / 26 | 185–191 |

S5 plato: olay ≥ 15 için R ort = 161,978 ms (n = 12). Kuyruk uzunluğu × periyot = 16 × 10 ms = 160 ms.

## Dışlanan kayıtlar

Zaman istatistiklerinden dışlandı; özet tablodaki olay sayılarında ve kayıp sütunlarında yer alır.

| Senaryo | Olay | Durum | Neden |
|---|---|---|---|
| S5 | 18 | tx_drop | eksik: t3,t4 |
| S5 | 20 | tx_drop | eksik: t3,t4 |
| S5 | 22 | tx_drop | eksik: t3,t4 |
| S5 | 23 | tx_drop | eksik: t3,t4 |
| S5 | 24 | tx_drop | eksik: t3,t4 |
| S5 | 25 | tx_drop | eksik: t3,t4 |
| S5 | 27 | tx_drop | eksik: t3,t4 |
| S5 | 28 | tx_drop | eksik: t3,t4 |
| S5 | 33 | tx_drop | eksik: t3,t4 |
| S5 | 34 | tx_drop | eksik: t3,t4 |
| S5 | 35 | tx_drop | eksik: t3,t4 |
| S5 | 36 | tx_drop | eksik: t3,t4 |
