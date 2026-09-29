# Hafta 1 — Yük Altında Buton Yanıt Süresi Analizi

FreeRTOS Bootcamp · Hafta 1 ödevi: bir uygulama ve bir mühendislik incelemesi.

STM32 + FreeRTOS üzerinde butona basıldığında orta öncelikli bir görev "butona basıldı" yanıtını üretir ve yanıt UART üzerinden PC arayüzüne gönderilir. Yanıt süresi, kart üzerindeki tek bir timer'dan alınan beş zaman damgasıyla (t₀–t₄) aşamalara bölünerek ölçülür. Telemetri hızı ve CPU yükü değiştirilerek altı senaryoda (S0–S5) gecikmenin **ne kadar**, **hangi koşulda** ve **hangi aşamada** değiştiği ham veri ve grafiklerle gösterilir.

**Hızlı bağlantılar:** [Kurulum](docs/setup.md) · [Kod notları](docs/code-notes.md) · [Analiz raporu](analysis/report.md) · [Ham ölçümler](measurements/) · [Grafikler](analysis/plots/) · [AI kullanımı](docs/ai-usage.md)

---

## 1. Donanım, Bağlantılar ve Araç Sürümleri

| Bileşen | Değer |
|---|---|
| Kart | NUCLEO-L476RG (STM32L476RG, Cortex-M4F) |
| MCU saati (SYSCLK) | 80 MHz (HSI16/MSI + PLL; HSE kullanılmıyor) |
| UART | USART2, TX: PA2, RX: PA3 — ST-LINK sanal COM portu üzerinden |
| Buton | B1 (mavi), PC13, basınca LOW, düşen kenar (EXTI13, `EXTI15_10_IRQn`) |
| LED | LD2 (yeşil), PA5 — hata göstergesi |
| IDE / derleyici | STM32CubeIDE 2.1.1 · GNU Tools for STM32 14.3.rel1 (arm-none-eabi-gcc) · STM32CubeMX 6.18.1 |
| STM32CubeL4 HAL | STM32Cube FW_L4 V1.18.2 |
| FreeRTOS | V10.3.1 · CubeMX arayüzü CMSIS_V2, uygulama görevleri doğrudan FreeRTOS API'siyle (`xTaskCreate`) |
| Derleme ayarı | Debug · `-O0 -g3` |
| PC arayüzü | Python 3.12.10 · tkinter · pyserial 3.5 · matplotlib 3.11.2 ([requirements.txt](interface/requirements.txt)) |
| PC işletim sistemi | Windows 11 Pro |

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
| TX yöntemi | IT; tamamlanana kadar görev bloklanır | Polling yükünü ayrı tutmak |
| Görev düzeni | Preemptive · 3 > 2 > 1 | Aynı öncelik ilişkisi |
| Deney deadline'ı | R = t₄ − t₀ ≤ 20 ms | Geç yanıtları saymak |
| Deney timeout'u | 1 s | Tamamlanmayan aktarımı sonlandırmak |
| Buton filtresi | İlk kenar kabul, 30 ms içindeki tekrar kenarlar sayılıp atılır | Tekrarlanabilir olay sayımı |

20 ms bu ödev için seçilmiş bir eşiktir; bir ürün standardı değildir.

Hat süresi referansı: 64 bayt × 10 bit / 115200 bit/s ≈ **5,56 ms** / mesaj.

---

## 3. Zaman Damgaları

Beş damga da kart üzerindeki aynı timer'dan alınır: TIM2, 32-bit, 1 MHz → 1 µs çözünürlük.

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

Ek CPU işi: sabit iterasyonlu tamsayı LCG döngüsü (`x = x·1664525 + 1013904223`). Sonuç `volatile` bir değişkene yazıldığı için derleyici döngüyü silemez. Kesmeler açık kalır, `vTaskDelay` kullanılmaz. Açılışta 20 000 iterasyon TIM2 ile 5 kez ölçülür ve en kısa süre alınır. Senaryonun iterasyon sayısı `hedef_µs × 20000 / ölçülen_µs` ile hesaplanır. Her çalışmada gerçek süre yeniden ölçülür ve `work_min_us` / `work_max_us` sayaçlarına yazılır.

### 4.1 Senaryo seçimi

Senaryo çalışma anında UART komutuyla seçilir. Firmware yeniden derlenmez.

| Komut | Etki |
|---|---|
| `SCN,Sx` | Senaryoyu seçer; olay kayıtlarını, sayaçları ve olay kimliklerini sıfırlar; TelemetryTask'ı uyandırır. Yanıt: `ACK,SCN,Sx` |
| `STOP` | Telemetriyi durdurur. Yanıt: `ACK,STOP` |
| `DUMP` | Yalnızca telemetri dururken: CSV başlığı, olay satırları, `CNT,...` sayaç satırı ve `END` |

Komutlar PC arayüzündeki düğmelerle ya da herhangi bir seri terminalden gönderilebilir.

### 4.2 Ölçüm adımları (her senaryoda aynı sıra)

1. Senaryoyu seçin. Önceki TX'i bitirin; kayıtları ve sayaçları sıfırlayın.
2. Frekansı, 64 bayt mesaj boyunu ve CPU işini doğrulayın. 5 saniye ısınma uygulayın.
3. En az 30 basış yapın; basışlar arasında en az 0,5 s olsun ve aralıkları değiştirin.
4. Telemetriyi durdurun; TX'i tamamlayın veya timeout kaydedin. Sonra kayıtları dışarı aktarın.
5. Ham CSV'yi `measurements/` altına kaydedin; grafikleri aynı ham veriden üretin.

Her kabul edilen olay `ok`, `btn_drop` (buton kuyruğu dolu), `tx_drop` (TX kuyruğu dolu), `tx_error` veya `timeout` olarak izlenir. Kayıplar sonuçtan gizlenmez ve "deadline karşılandı" olarak sayılmaz.

---

## 5. Kurulum ve Çalıştırma

Ayrıntılı adımlar: [docs/setup.md](docs/setup.md)

### 5.1 Firmware derleme ve yükleme
1. STM32CubeIDE'de *File → Import → Existing Projects into Workspace* ile `hafta-01/firmware` klasörünü içe aktar ("Copy projects into workspace" işaretsiz). Workspace klasörü repo dışında olmalı.
2. *Project → Build* (Debug).
3. *Run → Debug As → STM32 C/C++ Application* ile NUCLEO-L476RG'ye yükle.

### 5.2 PC arayüzünü başlatma
```bash
python -m pip install -r hafta-01/interface/requirements.txt
python hafta-01/interface/app.py
```
Ayrıntılar: [docs/setup.md](docs/setup.md#5-pc-arayüzünü-çalıştırma)

---

## 6. Timer ve FreeRTOS Ayarları

| Ayar | Değer |
|---|---|
| Zaman damgası timer'ı | TIM2 (32-bit), APB1 timer saati 80 MHz, PSC = 79 |
| Timer çözünürlüğü / taşma süresi | 1 µs / ≈ 71,6 dk |
| HAL timebase kaynağı | TIM6 (SysTick FreeRTOS'a ait) |
| `configTICK_RATE_HZ` | 1000 (1 tick = 1 ms) |
| `configUSE_PREEMPTION` | 1 |
| `configMAX_PRIORITIES` | 56 |
| `configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY` | 5 |
| Buton EXTI NVIC önceliği | 5 (`EXTI15_10_IRQn`) |
| UART NVIC önceliği | 6 (`USART2_IRQn`) |
| TIM6 (HAL timebase) NVIC önceliği | 15 |
| Timer daemon görevi önceliği | 2 (`configTIMER_TASK_PRIORITY`; software timer kullanılmadığı için sürekli bloklu) |
| Idle görevi önceliği | 0 |
| Flash ART (prefetch, I/D cache) | Açık (`PREFETCH_ENABLE`, `INSTRUCTION_CACHE_ENABLE`, `DATA_CACHE_ENABLE` = 1). Cortex-M4'te L1 cache yok, DMA kullanılmıyor |
| Görev yığın boyutları | TelemetryTask 512, ButtonTask 512, UartTxTask 512 word (1 word = 4 bayt). Kuru denemede high-water mark: 364 / 366 / 306 word boş |
| Heap | heap_4, `configTOTAL_HEAP_SIZE` = 32768 bayt |
| Stack overflow kontrolü | `configCHECK_FOR_STACK_OVERFLOW` = 2, `configUSE_MALLOC_FAILED_HOOK` = 1. Hook'larda LD2 sabit yanar |

---

## 7. Ham Veri, Grafikler ve Rapor

| İçerik | Konum |
|---|---|
| Ham ölçümler (senaryo başına) | [measurements/S0.csv … S5.csv](measurements/) |
| Özet tablo | [measurements/summary.csv](measurements/summary.csv) |
| Grafikler | [analysis/plots/](analysis/plots/) |
| Grafik üretme kodu | [analysis/analyze.py](analysis/analyze.py) (`python hafta-01/analysis/analyze.py`) |
| Betik çıktısı tablolar | [analysis/tables.md](analysis/tables.md) |
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
