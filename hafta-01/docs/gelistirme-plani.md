# Geliştirme Planı

Bu belge ödevin adım adım yapılış sırasını anlatır. Her adımda şunlar var: amaç, o adımda öğrenilecek RTOS kavramı, Claude Code'a verilecek mesaj ve adımın "bitti" sayılma kriteri.

Temel prensip: **ölçüm zincirini parça parça kur, her parçayı kartta doğrulamadan bir sonrakine geçme.** Senaryolar, zincirin kendisi güvenilir hale geldikten sonra çalıştırılır.

---

## Bölüm A — Bu ödevde RTOS nasıl çalışıyor?

### A.1 Temel kavramlar

**Görev (task).** Kendi sonsuz döngüsü ve kendi yığını (stack) olan bağımsız bir fonksiyondur. İşlemci tek çekirdeklidir; hangi görevin çalışacağına FreeRTOS'un scheduler'ı karar verir.

**Öncelik ve preemption.** Kural basittir: *çalışmaya hazır olan en yüksek öncelikli görev her zaman CPU'dadır.* Daha yüksek öncelikli bir görev hazır hale geldiği anda, düşük öncelikli görev işinin ortasında bile olsa kesilir (preemption). Bu ödevde TelemetryTask (3) > ButtonTask (2) > UartTxTask (1).

**Bloklanma.** Bir görev kuyrukta veri beklerken ya da `xTaskDelayUntil` ile beklerken **CPU kullanmaz**. Üç görevin olması CPU'nun dolu olduğu anlamına gelmez; görevlerin hepsi bloklu olduğunda CPU Idle görevindedir. Hocanın "`vTaskDelay()` CPU yükü üretmez" uyarısı bu yüzdendir: CPU yükü oluşturmak için gerçekten hesaplama yapan bir döngü gerekir.

**Kuyruk (queue).** Görevler ve ISR'ler arasında veriyi **kopyalayarak** taşıyan FIFO yapıdır. `xQueueSend(q, &veri, bekleme)` çağrısındaki son parametre, kuyruk doluysa ne kadar bekleneceğidir; `0` "hiç bekleme, hemen hata dön" demektir. `xQueueReceive(q, &veri, portMAX_DELAY)` ise veri gelene kadar görevi bloklar.

**ISR bir görev değildir.** Donanım kesmesi, hangi görev çalışıyor olursa olsun onu keser. ISR içinde bloklayan hiçbir fonksiyon çağrılamaz; bunun için API'lerin `FromISR` sürümleri vardır (`xQueueSendFromISR`, `vTaskNotifyGiveFromISR`). Bu fonksiyonlar, ISR'in daha yüksek öncelikli bir görevi uyandırıp uyandırmadığını bir bayrakla bildirir. `portYIELD_FROM_ISR(bayrak)` ise ISR biter bitmez, eski göreve dönmek yerine uyanan göreve geçilmesini sağlar.

**NVIC önceliği ≠ görev önceliği.** Kesme öncelikleri donanımın (NVIC), görev öncelikleri FreeRTOS'un konusudur. STM32'de NVIC'te küçük sayı daha yüksek önceliktir. `configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY` (CubeMX'te varsayılan 5) bir sınırdır: sayısal olarak bundan küçük öncelikli kesmeler FreeRTOS API'si çağıramaz. CubeMX'teki "Uses FreeRTOS functions" kutusu bu kuralı sizin yerinize uygular.

**Tick ve periyot.** FreeRTOS 1 ms'lik bir tick ile zamanı sayar. `vTaskDelay(10)` "şimdiden 10 tick sonra uyan" der; görevin kendi çalışma süresi eklendiği için periyot kayar. `xTaskDelayUntil(&last, 10)` ise "bir önceki uyanıştan 10 tick sonra uyan" der ve periyodu sabit tutar. Periyodik telemetri için doğru olan ikincisidir.

**Task notification.** Bir görevi uyandırmanın en hafif yoludur; ayrı bir kuyruk ya da semaphore nesnesi gerektirmez. Bu ödevde UART TC kesmesi, "gönderim bitti" bilgisini UartTxTask'a bununla verir.

### A.2 Bir buton basışının yolculuğu

```
Buton ──► EXTI ISR ──► buton kuyruğu ──► ButtonTask ──► TX kuyruğu ──► UartTxTask ──► UART hattı ──► TC ISR
            t₀                             t₁   t₂                        t₃                          t₄
```

1. **t₀:** Butona basılır ve EXTI kesmesi gelir. ISR zaman damgasını alır, filtreden geçirir, olayı buton kuyruğuna koyar ve biter. ButtonTask uyandıysa `portYIELD_FROM_ISR` ona geçişi sağlar.
2. **t₁ − t₀:** ButtonTask olayı alır. Ancak o anda daha yüksek öncelikli TelemetryTask çalışıyorsa (ör. S5'teki 5 ms'lik CPU işi), ButtonTask onun bitmesini bekler. **CPU yükünün etkisi bu aşamada görülür.**
3. **t₂ − t₁:** ButtonTask 64 baytlık yanıtı hazırlar. Bu aşama kısa olmalıdır; burada da TelemetryTask araya girebilir.
4. **t₃ − t₂:** Yanıt TX kuyruğuna girer. Kuyruk FIFO olduğu için, önünde bekleyen ya da o anda hatta olan bir TEL mesajı varsa sırasını bekler. Ayrıca UartTxTask en düşük öncelikli görevdir; diğer iki görevden biri çalışırken yeni gönderimi başlatamaz. **Telemetri frekansının etkisi bu aşamada görülür.**
5. **t₄ − t₃:** Mesaj hatta gider. 64 bayt × 10 bit / 115200 ≈ **5,56 ms**. Bu süre fizikseldir, senaryodan bağımsız olarak sabit kalmalıdır.

Bu bir **hipotezdir.** Ödevin amacı, gerçek kart verisiyle bunun doğru olup olmadığını ve her aşamanın *ne kadar* değiştiğini göstermektir.

---

## Bölüm B — Claude Code ile çalışma şekli

- Oturum: Code sekmesi → **Local** → proje klasörü olarak repo kökü.
- Her adıma yeni bir branch ile başla (GitHub Desktop'tan ya da Claude'a söyleyerek).
- Her adıma **Plan** modunda başla. Claude önce ne yapacağını ve hangi kavramları kullanacağını anlatır. Onayladıktan sonra **Accept edits** moduna geç.
- Claude kodu yazar; sen derler, karta yükler ve "bitti" kriterini kontrol edersin. Sonucu Claude'a yaz (değerler, hata mesajı, terminal çıktısı).
- Adım bitince commit, `main`'e merge ve sonraki adım.
- Anlamadığın bir yerde "bunu açıkla" demen yeterli. Kendin yazarak öğrenmek istersen oturumu **Learning** stiline al: Claude bazı parçaları `TODO(human)` olarak sana bırakır.

---

## Bölüm C — Adımlar

### Adım 0 — Hazırlık

- `CLAUDE.md`, `.claude/settings.json` ve `hafta-01/` dosyalarını repoya ekle ve commit et.
- `hafta-01/firmware/.gitkeep` dosyasını sil (CubeMX projesi bu klasöre üretilecek).

### Adım 1 — CubeMX yapılandırması ve iskelet · `feature/freertos-iskelet`

**Kavram:** Görev oluşturma, scheduler'ın başlaması, HAL timebase'in neden SysTick'ten alındığı.

**CubeMX'te senin yapacakların:**

| # | Nerede | Ayar |
|---|---|---|
| 1 | Yeni proje | Board Selector → 32F746G-DISCO. "Initialize all peripherals with their default Mode?" → **No** |
| 2 | Project Manager | Proje adı `firmware`, konum `.../hafta-01/`, Toolchain: STM32CubeIDE. Code Generator: "Generate peripheral initialization as a pair of .c/.h files" işaretli |
| 3 | RCC | HSE: Crystal/Ceramic Resonator |
| 4 | Clock Configuration | HCLK kutusuna 216 yaz, Enter. **APB1 Timer clocks = 108 MHz** olduğunu kontrol et |
| 5 | SYS | Debug: Serial Wire. Timebase Source: **TIM6** |
| 6 | CORTEX_M7 | CPU ICache: Enabled, CPU DCache: Enabled |
| 7 | USART1 | Mode: Asynchronous. **Pinlerin PA9 (TX) ve PB7 (RX) olduğunu kontrol et**; CubeMX RX'i PA10'a atayabilir. 115200, 8 bit, None, 1 stop. NVIC: USART1 global interrupt ✔ |
| 8 | GPIO | PI11 → GPIO_EXTI11, External Interrupt Rising edge, Pull-down. PI1 → GPIO_Output (LD1) |
| 9 | TIM2 | Clock Source: Internal Clock. Prescaler: 107. Counter Period: 4294967295. Kesme yok |
| 10 | FREERTOS | Interface: CMSIS_V2. USE_PREEMPTION: Enabled, TICK_RATE_HZ: 1000, CHECK_FOR_STACK_OVERFLOW: Option2, USE_MALLOC_FAILED_HOOK: Enabled, TOTAL_HEAP_SIZE: 32768. Tasks and Queues sekmesinde `defaultTask`'ı sil (silinemiyorsa bırak). Advanced Settings: USE_NEWLIB_REENTRANT: Enabled |
| 11 | NVIC | EXTI line[15:10]: ✔, öncelik 5. USART1: öncelik 6. İkisinde de "Uses FreeRTOS functions" ✔ |
| 12 | | Generate Code. CubeIDE'de projeyi bir kez derle |

**Claude Code'a:**

```
Adım 1'e başlıyoruz (docs/gelistirme-plani.md → Adım 1). CubeMX projesini ürettim ve derledim.
Önce üretilmiş kodu hafta-01/CLAUDE.md'deki donanım tablosuyla karşılaştır ve farkları söyle.
Sonra app_* dosya iskeletini, timer_us()'i, CubeIDE için .gitignore'u ve üç görevin boş
iskeletini ekle. Test için TelemetryTask LD1'i 500 ms'de bir yakıp söndürsün (Adım 4'te kaldırılacak).
Plan modundayım: önce planını ve kullanacağın RTOS kavramlarını anlat.
```

**Bitti sayılır:**
- LD1 saniyede bir yanıp sönüyor.
- CubeIDE debugger'da Live Expressions'a `TIM2->CNT` ekle: saniyede yaklaşık 1.000.000 artıyor.
- Derleme uyarısı yok.

### Adım 2 — UART TX zinciri · `feature/uart-tx`

**Kavram:** Kuyruk, UART'ın tek sahibi, IT gönderimi, task notification ile ISR'den görevi uyandırma.

**Claude Code'a:**

```
Adım 2: TX kuyruğu (16 × TxMsg), UartTxTask, HAL_UART_Transmit_IT ile gönderim, TC callback ve
1 s timeout. t3 ve t4'ü de kaydet. Test için geçici bir üretici her 100 ms'de 64 baytlık
"TEST,<n>,<önceki mesajın t4-t3 süresi us>" mesajı göndersin.
```

**Bitti sayılır:**
- Seri terminalde (PuTTY veya RealTerm, 115200) her satır tam 64 bayt, 10 satır/s.
- Ölçülen t₄ − t₃ değeri **≈ 5556 µs** civarında ve kararlı.

Bu, ölçüm zincirinin ilk gerçeklik testidir. Değer tutmuyorsa timer, saat ayarı veya TC mantığında bir hata var demektir; ilerlemeden önce düzelt.

### Adım 3 — Buton zinciri, olay kaydı ve DUMP · `feature/buton-zinciri`

**Kavram:** ISR'den kuyruğa gönderme, `FromISR` API'leri, `portYIELD_FROM_ISR`, debounce, olay kimliğiyle kayıt eşleştirme.

**Claude Code'a:**

```
Adım 3: EXTI callback'te t0 ve 30 ms filtre, buton kuyruğu (8), ButtonTask (t1, t2), BTN mesajı,
olay kaydı ve sayaçlar. RX ile satır okuma ve şimdilik yalnızca DUMP komutu. Adım 2'deki
geçici test üreticisini kaldır.
```

**Bitti sayılır:**
- Her basışta tek bir `BTN,<id>,S0,PRESSED` satırı geliyor.
- Hızlı ve kararsız basışlarda `bounce_rejected` artıyor.
- `DUMP` ile gelen satırlarda R ≈ 5,6 ms ve t₁ − t₀, t₂ − t₁, t₃ − t₂ değerleri küçük (onlarca µs mertebesinde).

### Adım 4 — Telemetri, senaryolar ve CPU işi · `feature/telemetri-yuk`

**Kavram:** `xTaskDelayUntil`, periyodik görev, preemption'ın ölçüme etkisi, CPU işinin kalibrasyonu.

**Claude Code'a:**

```
Adım 4: TelemetryTask (xTaskDelayUntil, S0'da bloklanma), senaryo tablosu, SCN ve STOP komutları,
kalibre CPU işi, periyot ve iş süresi min/max sayaçları. Adım 1'deki LED testini kaldır.
Kalibrasyonu nasıl yapacağını önce anlat.
```

**Bitti sayılır:**
- Her senaryoda TEL satırlarının sıklığı doğru (terminalde say ya da seq/tick_ms alanından hesapla).
- `DUMP` sayaçlarında ölçülen periyot 10 / 20 / 100 ms ± 1 tick.
- CPU işi süresi S4'te ≈ 2000 µs, S5'te ≈ 5000 µs.

### Adım 5 — PC arayüzü · `feature/pc-arayuz`

**Kavram:** (RTOS dışı) Seri port okuma ve mesaj ayrıştırma. Arayüz ölçümü gösterir, ölçüme karışmaz.

**Claude Code'a:**

```
Adım 5: interface/ altında Python arayüzü. Port seçimi, bağlan/kes, senaryo seçimi (SCN),
TEL/BTN ayrımı, "Butona basıldı · Olay N" gösterimi, STOP + DUMP ile measurements/Sx.csv kaydı,
R grafiği (20 ms çizgisi) ve kayıp sayaçları. requirements.txt ve çalıştırma adımlarını da ekle.
```

**Bitti sayılır:** Arayüzden bir senaryo başlatılıp basışlar yapılabiliyor, STOP + DUMP ile CSV kaydediliyor ve R grafiği görünüyor.

### Adım 6 — Kuru deneme ve firmware'i dondurma

- S0 ve S5'te 10'ar basışla kısa bir deneme yap. Aşama süreleri Bölüm A.2'deki beklentiyle kabaca uyuşuyor mu? Uyuşmuyorsa nedenini şimdi bul.
- README'deki timer ve FreeRTOS ayarları tablosunu doldur.
- Firmware'i commit et ve **`olcum-v1`** tag'ini koy. Bu noktadan sonra firmware değişirse ölçümler tekrarlanır.

### Adım 7 — Ölçüm

README'deki sırayı her senaryoda aynen uygula: sıfırla → doğrula → 5 s ısınma → en az 30 basış (aralarında en az 0,5 s, düzensiz aralıklarla) → STOP → DUMP → CSV kaydet. CSV'leri elle düzenleme.

### Adım 8 — Analiz · `analysis/rapor`

**Claude Code'a:**

```
Adım 8: analysis/ altında, measurements/S0–S5.csv dosyalarından summary.csv ve iki grafik
(olay no → R + 20 ms çizgisi; senaryo → aşama ortalamaları yığılmış sütun) üreten bir betik.
Dışlanan kayıtları ve nedenlerini ayrıca yazdır. Sonra report.md'deki tabloları betik
çıktısından doldur; yorum kısımlarını benimle birlikte yazacağız.
```

**Bitti sayılır:** Grafikler ve tablolar yalnızca betik çıktısından geliyor. Her bulgu "ne kadar, hangi koşulda, hangi aşamada" sorularını yanıtlıyor.

### Adım 9 — Teslim

- `setup.md`, `code-notes.md` ve `ai-usage.md` içindeki TBD'leri doldur. Claude `code-notes.md` için gerçek kaynak dosyalardan taslak çıkarabilir; açıklamayı kendi cümlelerinle son haline getir.
- Hocaya repo erişimi ver, teslim commit SHA'sını paylaş, kısa bir video çek (çalışan sistem ve senaryolar arasındaki fark).
