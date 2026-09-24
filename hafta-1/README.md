# Hafta 1 — Yük Altında Buton Yanıt Süresi Analizi

FreeRTOS Bootcamp · Hafta 1 ödevi: bir uygulama ve bir mühendislik incelemesi.

STM32 + FreeRTOS üzerinde butona basıldığında orta öncelikli bir görev "butona basıldı" yanıtını üretir ve yanıt UART üzerinden PC arayüzüne gönderilir. Yanıt süresi, kart üzerindeki tek bir timer'dan alınan beş zaman damgasıyla (t₀–t₄) aşamalara bölünerek ölçülür. Telemetri hızı ve CPU yükü değiştirilerek altı senaryoda (S0–S5) gecikmenin **ne kadar**, **hangi koşulda** ve **hangi aşamada** değiştiği ham veri ve grafiklerle gösterilir.

**Hızlı bağlantılar:** [Kurulum](docs/setup.md) · [Kod notları](docs/code-notes.md) · [Analiz raporu](analysis/report.md) · [Ham ölçümler](measurements/) · [Grafikler](analysis/plots/) · [AI kullanımı](docs/ai-usage.md)

---

## 1. Donanım, Bağlantılar ve Araç Sürümleri

| Bileşen | Değer |
|---|---|
| Kart | STM32F746 geliştirme kartı — _TBD: tam model (32F746G-DISCO / NUCLEO-F746ZG)_ |
| Not | Ödev referansı STM32L476RG'dir; kart temin edilemediği için STM32F746 kullanılmıştır. |
| MCU saati (SYSCLK) | _TBD_ MHz |
| UART | _TBD: USARTx_, TX: _TBD_, RX: _TBD_ — ST-LINK sanal COM portu üzerinden |
| Buton | _TBD: pin_ (EXTI hattı: _TBD_) |
| IDE / derleyici | _TBD: STM32CubeIDE sürümü, GCC sürümü_ |
| STM32CubeF7 HAL | _TBD: sürüm_ |
| FreeRTOS | _TBD: sürüm, CMSIS-RTOS arayüzü (v1/v2/doğrudan API)_ |
| Derleme ayarı | _TBD: Debug/Release, optimizasyon seviyesi_ |
| PC arayüzü | _TBD: dil, çalışma ortamı sürümü, kütüphaneler_ |
| PC işletim sistemi | _TBD_ |

---

## 2. Sistem Mimarisi

### 2.1 Görevler ve sorumluluklar

UART'ın tek sahibi `UartTxTask`'tır; diğer görevler UART'a doğrudan yazmaz.

| Görev | Öncelik | Sorumluluk |
|---|---|---|
| `TelemetryTask` | Yüksek · 3 | Periyodik telemetri üretir, ortak TX kuyruğuna bırakır. S4–S5'te ek CPU işini yapar. |
| `ButtonTask` | Orta · 2 | Buton olayını alır, yanıtı üretir, TX kuyruğuna bırakır. |
| `UartTxTask` | Düşük · 1 | TX kuyruğunu FIFO sırasıyla tüketir, UART gönderimini yönetir. |

3 uygulama görevi vardır (Idle görevi dahil değildir). Büyük sayı daha yüksek önceliktir. Buton ISR bir görev değildir.

### 2.2 Olay akışı

```
Buton ISR ──► Buton kuyruğu ──► ButtonTask ──► Ortak TX kuyruğu ──► UartTxTask ──► PC arayüzü
 (olay kimliği + t₀)  (8 olay)    (yanıt + t₁, t₂)    (16 mesaj, FIFO)   (gönderim + t₃, t₄)
                                        ▲
                     TelemetryTask ─────┘ (periyodik TEL mesajları)
```

### 2.3 Sabit deney ayarları

Senaryolar karşılaştırılırken bu ayarlar değiştirilmez.

| Ayar | Değer | Neden |
|---|---|---|
| UART | 115200 baud · 8N1 | Aynı hat süresi |
| Mesaj boyu | Her TEL / BTN mesajı 64 bayt (63 bayt ASCII, boşlukla doldurulmuş + LF) | Sabit paket boyu |
| Kuyruklar | Buton: 8 olay · TX: 16 mesaj · FIFO | Aynı tampon davranışı |
| TX yöntemi | _TBD: IT / DMA_; tamamlanana kadar görev bloklanır | Polling yükünü ayrı tutmak |
| Görev düzeni | Preemptive · 3 > 2 > 1 | Aynı öncelik ilişkisi |
| Deney deadline'ı | R = t₄ − t₀ ≤ 20 ms | Geç yanıtları saymak |
| Deney timeout'u | 1 s | Tamamlanmayan aktarımı sonlandırmak |
| Buton filtresi | İlk kenar kabul, 30 ms içindeki tekrar kenarlar sayılıp atılır | Tekrarlanabilir olay sayımı |

20 ms bu ödev için seçilmiş bir eşiktir; bir ürün standardı değildir.

Hat süresi referansı: 64 bayt × 10 bit / 115200 bit/s ≈ **5,56 ms** / mesaj.

---

## 3. Zaman Damgaları

Beş damga da kart üzerindeki aynı timer'dan alınır: _TBD: timer (ör. TIM2, 32-bit, 1 MHz → 1 µs çözünürlük)_.

| Nokta | Nerede kaydedilir | Yorum |
|---|---|---|
| t₀ | Buton ISR girişinde | Filtrenin kabul ettiği kenarın zamanı; fiziksel basış anı değildir |
| t₁ | `ButtonTask` olayı aldıktan hemen sonra | Olay aktarımı ve CPU beklemesi dahildir |
| t₂ | Yanıt için `xQueueSend` çağrısından hemen önce | Başarılı gönderimde ölçüm zinciri devam eder |
| t₃ | UART başlatma çağrısından hemen önce | İlk fiziksel bit ile aynı an değildir |
| t₄ | UART TC (transmission complete) işlenirken | Son bit sonrası ISR/callback gözlem zamanı |

| Hesap | Anlamı |
|---|---|
| t₁ − t₀ | ISR'den görevin olayı almasına kadar gözlenen süre |
| t₂ − t₁ | Yanıt hazırlama aralığı (preemption dahil olabilir) |
| t₃ − t₂ | Kuyruğa verme + bekleme + UART başlatma öncesi süre |
| t₄ − t₃ | UART başlatma, hat aktarımı ve TC gözlem süresi |
| R = t₄ − t₀ | Kart tarafında toplam gözlenen yanıt süresi |

Ölçüm kuralları:

- PC ve MCU saatleri birbirinden çıkarılmaz.
- Farklar uint32 üzerinde mod 2³² hesaplanır; bir olayın süresi bir sayaç turundan kısadır.
- Eksik zaman 0 yazılmaz, boş bırakılır.
- Kayıtlar RAM'de tutulur (en az 64 olay + taşma sayacı), telemetri durdurulup TX tamamlandıktan sonra dışarı aktarılır.

---

## 4. Senaryolar

Önce frekans, sonra CPU yükü değiştirilir.

| ID | Telemetri | Ek CPU işi | Hedef |
|---|---|---|---|
| S0 | Kapalı | Yok | Referans yanıt süresi |
| S1 | 10 Hz · 100 ms | Yok | Düşük telemetri sıklığı |
| S2 | 50 Hz · 20 ms | Yok | Orta telemetri sıklığı |
| S3 | 100 Hz · 10 ms | Yok | Yüksek telemetri sıklığı |
| S4 | 100 Hz · 10 ms | ≈ 2 ms / periyot | Ek CPU yükü |
| S5 | 100 Hz · 10 ms | ≈ 5 ms / periyot | Daha yüksek CPU yükü |

Ek CPU işi: _TBD: kullanılan hesaplama işi ve kalibrasyon yöntemi (iterasyon sayısı ↔ ölçülen süre)_.

### 4.1 Senaryo seçimi

_TBD: senaryonun nasıl seçildiği (PC arayüzünden komut / derleme sabiti / buton kombinasyonu)._

### 4.2 Ölçüm adımları (her senaryoda aynı sıra)

1. Senaryoyu seçin. Önceki TX'i bitirin; kayıtları ve sayaçları sıfırlayın.
2. Frekansı, 64 bayt mesaj boyunu ve CPU işini doğrulayın. 5 saniye ısınma uygulayın.
3. En az 30 basış yapın; basışlar arasında en az 0,5 s olsun ve aralıkları değiştirin.
4. Telemetriyi durdurun; TX'i tamamlayın veya timeout kaydedin. Sonra kayıtları dışarı aktarın.
5. Ham CSV'yi `measurements/` altına kaydedin; grafikleri aynı ham veriden üretin.

Her kabul edilen olay `ok`, `drop`, `tx_error` veya `timeout` olarak izlenir. Kayıplar sonuçtan gizlenmez ve "deadline karşılandı" olarak sayılmaz.

---

## 5. Kurulum ve Çalıştırma

Ayrıntılı adımlar: [docs/setup.md](docs/setup.md)

### 5.1 Firmware derleme ve yükleme
_TBD_

### 5.2 PC arayüzünü başlatma
_TBD_

---

## 6. Timer ve FreeRTOS Ayarları

| Ayar | Değer |
|---|---|
| Zaman damgası timer'ı | _TBD_ |
| Timer çözünürlüğü / taşma süresi | _TBD_ |
| HAL timebase kaynağı | _TBD (SysTick FreeRTOS'a ait; ör. TIM6)_ |
| `configTICK_RATE_HZ` | _TBD_ |
| `configUSE_PREEMPTION` | 1 |
| `configMAX_PRIORITIES` | _TBD_ |
| `configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY` | _TBD_ |
| Buton EXTI NVIC önceliği | _TBD_ |
| UART NVIC önceliği | _TBD_ |
| D-Cache | _TBD: açık/kapalı; DMA kullanılıyorsa tampon yönetimi_ |
| Görev yığın boyutları | _TBD_ |

---

## 7. Ham Veri, Grafikler ve Rapor

| İçerik | Konum |
|---|---|
| Ham ölçümler (senaryo başına) | [measurements/S0.csv … S5.csv](measurements/) |
| Özet tablo | [measurements/summary.csv](measurements/summary.csv) |
| Grafikler | [analysis/plots/](analysis/plots/) |
| Grafik üretme kodu | _TBD_ |
| Analiz raporu | [analysis/report.md](analysis/report.md) |

Ham CSV biçimi (her satır bir buton olayı):

```
scenario,event_id,t0_us,t1_us,t2_us,t3_us,t4_us,status
```

---

## 8. Repo Yapısı

```
hafta-01/
├── README.md
├── firmware/            # STM32 + FreeRTOS projesi
├── interface/           # UART telemetri PC arayüzü
├── measurements/
│   ├── S0.csv … S5.csv  # Ham ölçümler
│   └── summary.csv      # Senaryo özet tablosu
├── analysis/
│   ├── report.md        # Mühendislik incelemesi
│   └── plots/           # Ham veriden üretilen grafikler
└── docs/
    ├── setup.md         # Kurulum ve donanım ayarları
    ├── code-notes.md    # Kritik kod blokları ve açıklamaları
    └── ai-usage.md      # Yapay zekâ kullanım beyanı
```

---

## 9. Teslim

- Teslim commit'i: _TBD: SHA_
- Anlatım videosu: _TBD: bağlantı_