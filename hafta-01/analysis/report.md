# Analiz Raporu: Yük Altında Buton Yanıt Süresi

> Tablolardaki ve grafiklerdeki bütün sayılar `analysis/analyze.py` betiğinin `measurements/` altındaki ham CSV dosyalarından ürettiği çıktıdır (bkz. [tables.md](tables.md)). Ham CSV'ler elle düzenlenmemiştir.

## 1. Deney Koşulları

- Kart, MCU saati, tick hızı, timer ve derleme ayarları: bkz. [README](../README.md#1-donanım-bağlantılar-ve-araç-sürümleri)
- Ölçülen firmware: `olcum-v1` tag'i (`9124f34`). NUCLEO-L476RG, 80 MHz, FreeRTOS 10.3.1, Debug `-O0`
- Teslim commit'i: _TBD_
- Ölçüm tarihi: 2026-09-29
- Prosedür: her senaryoda `SCN,Sx` → 5 s ısınma → en az 30 basış (en az 0,5 s aralıklı, düzensiz) → `STOP` → `DUMP`. CSV'ler PC arayüzü tarafından DUMP çıktısından olduğu gibi kaydedildi.

## 2. Özet Tablo

Birim: ms. Kaynak: [measurements/summary.csv](../measurements/summary.csv). R istatistikleri yalnızca başarılı (`ok`) olaylar üzerinden hesaplandı. p95 en yakın sıra yöntemiyle alındı, yani gözlenmiş bir örnektir.

| Senaryo | Kabul edilen olay | Başarılı (ok) | R min | R ort | R medyan | R p95 | R maks (gözlenen) | > 20 ms | drop | tx_error | timeout | Kayıt kaybı |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S0 | 35 | 35 | 5,675 | 5,676 | 5,676 | 5,679 | 5,680 | 0 | 0 | 0 | 0 | 0 |
| S1 | 30 | 30 | 5,675 | 5,837 | 5,676 | 7,783 | 8,325 | 0 | 0 | 0 | 0 | 0 |
| S2 | 30 | 30 | 5,675 | 6,102 | 5,676 | 10,333 | 10,730 | 0 | 0 | 0 | 0 | 0 |
| S3 | 30 | 30 | 5,675 | 7,114 | 6,639 | 9,958 | 10,662 | 0 | 0 | 0 | 0 | 0 |
| S4 | 32 | 32 | 5,675 | 8,178 | 7,350 | 12,773 | 13,011 | 0 | 0 | 0 | 0 | 0 |
| S5 | 30 | 28 | 19,240 | 121,767 | 151,999 | 164,969 | 164,997 | 27 | 2 | 0 | 0 | 0 |

Dışlanan kayıtlar ve nedenleri: S5 olay 17 ve 28, durum `tx_drop` (TX kuyruğu dolu). Bu iki olayda t₃ ve t₄ alınmadı, bu yüzden R hesaplanamaz. Zaman istatistiklerinden dışlandılar ama kabul edilen olay sayısında ve `drop` sütununda yer alıyorlar. "Deadline karşılandı" olarak sayılmadılar. Aynı senaryoda kart ayrıca 14 TEL mesajını da düşürdü (`tx_drop_tel = 14`).

## 3. Aşama Süreleri

Birim: ms, başarılı olayların ortalaması.

| Senaryo | t₁ − t₀ | t₂ − t₁ | t₃ − t₂ | t₄ − t₃ | R |
|---|---|---|---|---|---|
| S0 | 0,024 | 0,037 | 0,056 | 5,559 | 5,676 |
| S1 | 0,025 | 0,037 | 0,215 | 5,559 | 5,837 |
| S2 | 0,024 | 0,037 | 0,481 | 5,559 | 6,102 |
| S3 | 0,024 | 0,039 | 1,492 | 5,559 | 7,114 |
| S4 | 0,167 | 0,038 | 2,414 | 5,559 | 8,178 |
| S5 | 0,698 | 0,038 | 115,472 | 5,559 | 121,767 |

Gözlenen maksimumlar (ms): t₁ − t₀ S3'te 0,027, S4'te 1,775, S5'te 4,438. t₃ − t₂ S1'de 2,701, S2'de 5,106, S3'te 5,038, S4'te 5,640, S5'te 159,369.

Kart sayaçları: telemetri periyodu bütün senaryolarda hedefin ± 3 µs içinde kaldı. CPU işi S4'te 2002–2064 µs, S5'te 5002–5090 µs sürdü. `bounce_rejected` bütün senaryolarda 0.

## 4. Grafikler

### 4.1 Olay numarası → R (20 ms deadline çizgisiyle)
![Olay → R](plots/r_per_event.png)

### 4.2 Senaryo → aşama ortalamaları (yığılmış)
![Senaryo → aşamalar](plots/stage_means.png)

Grafik üretme kodu: [analysis/analyze.py](analyze.py). Çizim fonksiyonları PC arayüzüyle ortak: [interface/plots.py](../interface/plots.py).

## 5. Bulgular

Her bulgu şu sorulara yanıt verir: **Ne kadar? Hangi koşulda? Hangi aşamada?**

> Taslak: Bu bölümdeki yorumlar tablolardaki sayılara dayanılarak Claude tarafından yazıldı. Kullanıcı gözden geçirip kendi cümleleriyle son haline getirecek.

### 5.1 Telemetri frekansının etkisi (S0 → S1 → S2 → S3)

- **Değişen aşama yalnızca t₃ − t₂.** Ortalaması 0,056 → 0,215 → 0,481 → 1,492 ms oldu, yani S0'dan S3'e yaklaşık 27 kat arttı. Aynı senaryolarda t₁ − t₀ (0,024–0,025 ms), t₂ − t₁ (0,037–0,039 ms) ve t₄ − t₃ (5,559 ms) sabit kaldı.
- **Mekanizma:** BTN yanıtı, TEL mesajlarıyla aynı FIFO TX kuyruğunu ve aynı UART hattını paylaşıyor. Butona basıldığında hatta bir TEL mesajı varsa BTN onun bitmesini bekliyor. Bu bekleme en fazla bir mesaj süresi kadar olabilir (≈ 5,56 ms). Gözlenen t₃ − t₂ maksimumları da bu sınırın altında: 2,701 / 5,106 / 5,038 ms.
- **Ne kadar sık?** t₃ − t₂ süresi 1 ms'yi aşan olay sayısı S1'de 2/30, S2'de 4/30, S3'te 15/30. Hat doluluğu ise sırasıyla %5,6, %27,8 ve %55,6 (5,56 ms / periyot). S1 ve S3'teki oranlar hat doluluğuna yakın. S2'deki oran beklenenden düşük; 30 örnekle bu sapma rastlantısal olabilir.
- **Deadline:** S0–S3'te bütün olaylar 20 ms'nin altında kaldı. En büyük gözlenen R 10,730 ms (S2).

### 5.2 CPU yükünün etkisi (S3 → S4 → S5)

- **t₁ − t₀ büyüdü.** Ortalama 0,024 → 0,167 → 0,698 ms, maksimum 0,027 → 1,775 → 4,438 ms. Maksimumlar CPU işinin süresiyle sınırlı (≈ 2 ve ≈ 5 ms). Butona iş sırasında basılırsa ButtonTask (öncelik 2), TelemetryTask'ın (öncelik 3) işini bitirmesini bekliyor. Bu doğrudan preemption etkisi.
- **t₃ − t₂ çok daha fazla büyüdü.** S3 → S4 arasında ortalama 1,492 → 2,414 ms. S5'te 115,472 ms'ye çıktı, gözlenen maksimum 159,369 ms.
- **S5'te sistem doyuma ulaştı:** 28 başarılı olayın 27'si 20 ms'yi aştı. 2 BTN yanıtı (`tx_drop`) ve 14 TEL mesajı TX kuyruğu dolduğu için düşürüldü. Grafik 4.1'de R her basışta yaklaşık 10 ms artıyor ve 15. olaydan sonra ≈ 160 ms'de düzleşiyor (olay ≥ 15 için R ort 163,1 ms).
- **Mekanizma:** S5'te her 10 ms'lik periyodun ilk ≈ 5 ms'sinde TelemetryTask CPU işini yapıyor. UartTxTask en düşük öncelikte olduğu için TC kesmesi bu sırada gelse bile yeni gönderimi başlatamıyor ve UART hattı boşta bekliyor. Veri bunu gösteriyor: S5'teki 28 başarılı olayın hepsinde t₃, 10 ms'lik periyodun 7183–7190 µs aralığına düşüyor. UartTxTask yalnızca iş bittikten hemen sonra CPU alabiliyor. Bu durumda hat periyot başına yalnızca 1 mesaj gönderebiliyor. Telemetri de periyot başına 1 mesaj ürettiği için her BTN mesajı kuyruğa kalıcı bir fazlalık ekliyor. Kuyruk 16 mesajda doluyor (16 × 10 ms ≈ 160 ms). Bu noktadan sonra yeni mesajlar düşürülüyor.

## 6. Değerlendirme

- **Hangi bileşen değişti?** En büyük değişim t₃ − t₂'de, yani ortak TX kuyruğunda bekleme ve UartTxTask'ın CPU'ya erişim süresinde. t₁ − t₀ yalnızca CPU yükü olan senaryolarda ve iş süresiyle sınırlı ölçüde büyüdü. t₂ − t₁ ile t₄ − t₃ hiçbir senaryoda değişmedi.
- **Neden?** İki tasarım kararı birleşiyor: (1) BTN ve TEL mesajları tek bir FIFO kuyrukta öncelik farkı olmadan sıraya giriyor. (2) UART'ın tek sahibi en düşük öncelikli görev. Hat kapasitesi S5'te bile %55,6 kullanımla yeterliydi. Darboğaz UART değil, UartTxTask'ın CPU'ya erişemediği sürelerde hattın boşta kalması.
- **Hangi ölçüm destekliyor?** Aşama tablosu (bölüm 3), S5'te t₃'lerin 7 µs'lik bir faz bandında toplanması, S5 platosunun kuyruk uzunluğu × periyot ile örtüşmesi ve kart sayaçları (`tx_drop_tel = 14`, `tx_drop_btn = 2`).
- **Ne henüz bilinmiyor?**
  - Önerilebilecek düzeltmelerin etkisi ölçülmedi: UartTxTask önceliğini yükseltmek, BTN için ayrı ya da öncelikli bir kuyruk, UART DMA ile ardışık gönderim, TEL için kuyruk doluluğuna bağlı atlama.
  - S5'te doyum başladıktan sonra R, basış sayısına bağlı. Ortalama ve medyan senaryonun sabit bir özelliği değil, ölçüm uzunluğunun bir sonucu. Daha uzun ya da daha kısa ölçümler farklı ortalama verir.
  - Optimizasyonlu derlemenin (`-Os`) aşama sürelerine etkisi ölçülmedi.

## 7. Ölçümün Sınırları

- Gözlenen maksimum, kanıtlanmış worst-case değildir. Her senaryoda 30–35 olay ölçüldü.
- t₀, fiziksel basış anı değil, filtrenin kabul ettiği kenarın ISR giriş zamanıdır. Buton hattındaki donanım gecikmesi (varsa RC filtre) t₀'dan önce kalır ve R'ye dahil değildir.
- t₃, ilk fiziksel bitin çıktığı an değildir. t₄ kesme gözlem gecikmesini içerir. t₄ − t₃ ile teorik hat süresi (5,556 ms) arasındaki ≈ 3–4 µs fark bu ek süreleri gösterir.
- Kayıp yanıtlar "deadline karşılandı" olarak sayılmamıştır.
- Firmware Debug (`-O0`) yapılandırmasıyla derlendi. Yazılım aşamalarının mutlak süreleri optimizasyonlu derlemede farklı olur.
- S5 ortalamaları doyum rejiminde basış sayısına bağlıdır (bkz. bölüm 6).
- Basış aralıkları elle üretildi. Aralıkların düzensizliği ölçülmedi, yalnızca PC arayüzü 0,5 s altı basışlarda uyarı verdi.
- `bounce_rejected = 0`: test edilen basışlarda filtreye takılan kenar gözlenmedi. Bu, kartın buton devresi hakkında bir iddia değildir.
