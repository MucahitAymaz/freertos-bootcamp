# Analiz Raporu: Yük Altında Buton Yanıt Süresi

> Bu rapor ölçümler tamamlandıktan sonra doldurulacaktır. Tüm sayılar `measurements/` altındaki ham CSV dosyalarından üretilir.

## 1. Deney Koşulları

- Kart, MCU saati, tick hızı, timer ve derleme ayarları: bkz. [README](../README.md#1-donanım-bağlantılar-ve-araç-sürümleri)
- Teslim commit'i: _TBD_
- Ölçüm tarihi: _TBD_

## 2. Özet Tablo

Birim: ms. Kaynak: [measurements/summary.csv](../measurements/summary.csv)

| Senaryo | Kabul edilen olay | Başarılı (ok) | R min | R ort | R maks (gözlenen) | > 20 ms | drop | tx_error | timeout | Kayıt kaybı |
|---|---|---|---|---|---|---|---|---|---|---|
| S0 | | | | | | | | | | |
| S1 | | | | | | | | | | |
| S2 | | | | | | | | | | |
| S3 | | | | | | | | | | |
| S4 | | | | | | | | | | |
| S5 | | | | | | | | | | |

Dışlanan kayıtlar ve nedenleri: _TBD_

## 3. Aşama Süreleri

Birim: ms, ortalama (başarılı olaylar üzerinden).

| Senaryo | t₁ − t₀ | t₂ − t₁ | t₃ − t₂ | t₄ − t₃ | R |
|---|---|---|---|---|---|
| S0 | | | | | |
| S1 | | | | | |
| S2 | | | | | |
| S3 | | | | | |
| S4 | | | | | |
| S5 | | | | | |

## 4. Grafikler

### 4.1 Olay numarası → R (20 ms deadline çizgisiyle)
_TBD: `plots/` altındaki görsel_

### 4.2 Senaryo → aşama ortalamaları (yığılmış sütun)
_TBD: `plots/` altındaki görsel_

Grafik üretme kodu: _TBD_

## 5. Bulgular

Her bulgu şu sorulara yanıt verir: **Ne kadar? Hangi koşulda? Hangi aşamada?**

### 5.1 Telemetri frekansının etkisi (S0 → S1 → S2 → S3)
_TBD_

### 5.2 CPU yükünün etkisi (S3 → S4 → S5)
_TBD_

## 6. Değerlendirme

- Hangi bileşen değişti? _TBD_
- Neden? _TBD_
- Hangi ölçüm destekliyor? _TBD_
- Ne henüz bilinmiyor? _TBD_

## 7. Ölçümün Sınırları

- Gözlenen maksimum, kanıtlanmış worst-case değildir.
- t₀, fiziksel basış anı değil, filtrenin kabul ettiği kenarın ISR giriş zamanıdır.
- t₃, ilk fiziksel bitin çıktığı an değildir; t₄ kesme gözlem gecikmesini içerir.
- Kayıp yanıtlar "deadline karşılandı" olarak sayılmamıştır.
- _TBD: diğer sınırlar_
