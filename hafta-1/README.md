# Yük Altında Buton Yanıt Süresi Analizi

FreeRTOS Bootcamp ödevi: bir uygulama ve bir mühendislik incelemesi.

STM32 tabanlı bir kart üzerinde FreeRTOS ile çalışan bir sistemde, butona basılmasından "butona basıldı" yanıtının PC'ye ulaşmasına kadar geçen süre ölçülür. Ölçüm, **UART telemetri hızı** ve **CPU yükü** değiştirilerek tekrarlanır. Amaç yalnızca toplam gecikmenin arttığını göstermek değil, gecikmenin **ne kadar**, **hangi koşulda** ve **hangi aşamada** değiştiğini grafik ve ham veriyle ortaya koymaktır.

---

## 1. Amaç

- Karttan UART ile telemetri alan bir PC arayüzü geliştirmek.
- Butona basıldığında **orta öncelikli** bir FreeRTOS görevinin "butona basıldı" yanıtını üretmesini sağlamak.
- Telemetri hızını ve CPU yükünü değiştirerek buton yanıt süresini ölçmek.
- Gecikmeyi aşamalara ayırıp her aşamanın koşullara göre nasıl değiştiğini açıklamak.

> "100 Hz'de daha yavaş" yeterli bir sonuç değildir. Her bulgu şu üç soruyu yanıtlamalıdır: **Ne kadar?** (µs/ms, ortalama, en kötü durum) **Hangi koşulda?** (telemetri hızı, CPU yükü) **Hangi aşamada?** (aşağıdaki aşama tanımlarına göre)

---

## 2. Donanım ve Yazılım

| Bileşen | Kullanılan |
|---|---|
| Geliştirme kartı | STM32F746 geliştirme kartı *(hocanın önerdiği STM32L476RG temin edilince ona taşınabilir)* |
| RTOS | FreeRTOS |
| IDE / derleyici | _TBD_ |
| PC ↔ kart bağlantısı | UART (baud hızı: _TBD_) |
| PC arayüzü | _TBD (dil / kütüphane)_ |
| Harici ölçüm aracı | _TBD (lojik analizör / osiloskop, varsa)_ |

---

## 3. Sistem Mimarisi

### 3.1 Görevler

| Görev / kesme | Öncelik | Görevi |
|---|---|---|
| Buton EXTI kesmesi (ISR) | Kesme | Buton kenarını yakalar, zaman damgası alır, orta öncelikli görevi uyandırır |
| Buton yanıt görevi | **Orta** | "Butona basıldı" yanıtını üretir ve UART'a gönderir |
| Telemetri görevi | _TBD_ | Ayarlanabilir hızda periyodik telemetri paketi gönderir |
| Yük görevi | _TBD_ | Ayarlanabilir oranda CPU yükü oluşturur |

> Görev önceliklerinin birbirine göre konumu ölçüm sonuçlarını doğrudan etkiler; son hali deney sırasında burada kaydedilecektir.

### 3.2 Gecikme Aşamaları

Buton yanıt süresi aşağıdaki zaman damgalarıyla aşamalara bölünür:

| Damga | Olay |
|---|---|
| T0 | Buton kesmesi (ISR) girişi |
| T1 | ISR'den görev bildirimi gönderildi |
| T2 | Orta öncelikli görev çalışmaya başladı |
| T3 | Yanıt mesajı UART gönderim tamponuna/kuyruğuna yazıldı |
| T4 | Yanıt mesajının UART iletimi tamamlandı |
| T5 | Yanıt PC arayüzünde alındı |

| Aşama | Aralık | Olası etken |
|---|---|---|
| Kesme gecikmesi | Fiziksel basış → T0 | Kesme önceliği, kritik bölgeler |
| Zamanlama (scheduling) gecikmesi | T1 → T2 | CPU yükü, daha yüksek öncelikli görevler |
| İşleme süresi | T2 → T3 | Yanıt görevinin kendi kodu |
| UART kuyruk bekleme | T3 → T4 (iletim öncesi kısım) | Telemetri trafiği, tampon doluluğu |
| UART iletim süresi | T3 → T4 (iletim kısmı) | Baud hızı, mesaj uzunluğu |
| PC tarafı | T4 → T5 | USB-UART köprüsü, işletim sistemi, arayüz |

Kart üzerindeki damgalar (T0–T4) aynı saatten alınır. PC damgası (T5) farklı bir saate ait olduğundan PC tarafı ayrı değerlendirilir.

---

## 4. Deney Planı

Bağımsız değişkenler:

- **Telemetri hızı:** _TBD (ör. kapalı, düşük, orta, yüksek Hz)_
- **CPU yükü:** _TBD (ör. %0, %25, %50, %75, %90)_

Her koşul kombinasyonunda yeterli sayıda buton basışı kaydedilir. Her aşama için ortalama, medyan, en kötü durum ve dağılım raporlanır. Ham veriler `data/` klasöründe saklanır.

---

## 5. Kurulum ve Çalıştırma

> _Bu bölüm proje yapısı netleştikçe doldurulacaktır._

### 5.1 Firmware
_TBD: projeyi derleme ve karta yükleme adımları_

### 5.2 PC Arayüzü
_TBD: bağımlılıkların kurulumu, seri port seçimi, arayüzü çalıştırma_

---

## 6. Repo Yapısı (planlanan)

```
.
├── firmware/      # STM32 + FreeRTOS projesi
├── pc-gui/        # UART telemetri arayüzü
├── data/          # Ham ölçüm verileri
├── analysis/      # Grafik ve analiz betikleri
└── README.md
```

---

## 7. Sonuçlar

> _Ödev tamamlandığında eklenecek: grafikler, ham veri özetleri ve aşama bazlı gecikme analizi._

## 8. Değerlendirme ve Sonuç

> _Ödev tamamlandığında eklenecek._
