# Hafta 1 — Yük Altında Buton Yanıt Süresi

- Görev tanımı ve teslim yapısı: `README.md`
- Adım adım plan ve her adımın bitti kriteri: `docs/gelistirme-plani.md`

Kullanıcı "Adım N" dediğinde plandaki Adım N'yi uygula ve yalnızca onun kapsamında kal. Bu dosyadaki kurallar ödevin sabit gereksinimleridir; değiştirmen gerektiğini düşünürsen önce gerekçeni anlat ve onay al.

## Donanım: 32F746G-DISCO

| | |
|---|---|
| MCU | STM32F746NG, Cortex-M7, HSE 25 MHz, SYSCLK 216 MHz |
| UART | USART1: PA9 TX, PB7 RX (ST-LINK sanal COM portu) |
| Buton | B1 (mavi): PI11, basınca HIGH → EXTI11, yükselen kenar, `EXTI15_10_IRQn` |
| LED | LD1 (yeşil): PI1, hata göstergesi olarak kullanılır |
| Zaman damgası | TIM2, 32-bit, APB1 timer saati 108 MHz, PSC = 107 → 1 MHz (1 µs), taşma ≈ 71,6 dk |
| HAL timebase | TIM6 (SysTick FreeRTOS'a aittir) |
| Önbellek | I-Cache ve D-Cache açık. UART IT modunda çalıştığı için DMA/cache tutarlılığı sorunu yoktur |

Bu değerleri kesin kabul etme. Kod yazmadan önce `firmware/` altındaki üretilmiş kodla (`main.c`, `stm32f7xx_hal_msp.c`, `FreeRTOSConfig.h`) karşılaştır; fark varsa kullanıcıya söyle.

## Derleme

- Proje `firmware/` altında bir STM32CubeIDE projesidir.
- `firmware/Debug/makefile` varsa ve `make` ile `arm-none-eabi-gcc` PATH'teyse `make -C firmware/Debug -j8 all` ile derle. Yoksa kullanıcıdan CubeIDE'de derlemesini (Ctrl+B) ve hata çıktısını yapıştırmasını iste.
- Hedef: sıfır uyarı (warning).

## Kod yerleşimi

Uygulama kodu CubeMX dosyalarından ayrı tutulur. `Core/Src` ve `Core/Inc` altı CubeIDE tarafından otomatik derlenir.

| Dosya | İçerik |
|---|---|
| `Core/Inc/app_config.h` | Tüm sabitler: öncelikler, kuyruk boyları, mesaj boyu, deadline, timeout, filtre süresi, senaryo tablosu |
| `Core/Src/app_main.c` | `app_start()`: kuyrukları ve görevleri oluşturur |
| `Core/Src/app_time.c` | `timer_us()` |
| `Core/Src/app_button.c` | EXTI callback (ISR yolu) ve ButtonTask |
| `Core/Src/app_telemetry.c` | TelemetryTask ve kalibre edilmiş CPU işi |
| `Core/Src/app_uart.c` | UartTxTask, TC ve RX callback'leri, komut işleme, kayıt aktarımı |
| `Core/Src/app_eventlog.c` | Olay kayıtları ve sayaçlar |

- `app_start()`, `freertos.c` içindeki `USER CODE BEGIN RTOS_THREADS` bloğundan çağrılır.
- HAL weak callback'leri (`HAL_GPIO_EXTI_Callback`, `HAL_UART_TxCpltCallback`, `HAL_UART_RxCpltCallback`) yalnızca app dosyalarında tanımlanır.
- Float kullanma; `snprintf` yalnızca tamsayı biçimleriyle.

## Görevler (sabit)

| Görev | Öncelik | Sorumluluk |
|---|---|---|
| TelemetryTask | `tskIDLE_PRIORITY + 3` | Periyodik TEL mesajı ve S4–S5'te CPU işi |
| ButtonTask | `tskIDLE_PRIORITY + 2` | Buton olayı → BTN yanıtı |
| UartTxTask | `tskIDLE_PRIORITY + 1` | UART'ın tek sahibi: TX kuyruğunu tüketir, komutları işler |

- Görevler native FreeRTOS API'siyle (`xTaskCreate`) oluşturulur.
- Uygulama görevi sayısı 3'tür; dördüncü bir görev ekleme.
- CubeMX'in `defaultTask`'ı ölçüme karışmamalı: CubeMX'te silinmiş olmalı; silinmemişse gövdesinin ilk satırı `vTaskDelete(NULL)` olsun.
- Timer daemon ve Idle görevlerinin önceliklerini kullanıcıya raporla (README'ye yazılacak).

## Kesmeler

- ISR'ler kısa olur: bekleme yok, UART yazma yok, `printf` yok, yalnızca `...FromISR` API'leri.
- EXTI15_10 ve USART1 NVIC öncelikleri sayısal olarak `configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY` değerinden (CubeMX varsayılanı 5) küçük olamaz.
- Buton filtresi: ilk yükselen kenar kabul edilir ve t₀ alınır. Son kabulden sonraki 30 ms içinde gelen kenarlar `bounce_rejected` sayacına yazılıp atılır.

## Kuyruklar ve mesajlar

- Buton kuyruğu: 8 × `ButtonEvent { uint32_t id; uint32_t t0; }`
- TX kuyruğu: 16 × `TxMsg`, FIFO. `TxMsg` verinin kendisini taşır (`char data[64]`), işaretçi değil. Ayrıca `type` (TEL / BTN / CMD) ve `event_id` alanları vardır.
- TEL ve BTN mesajları tam 64 bayttır: 63 bayt ASCII (boşlukla doldurulur) + `\n`. İçerik 63 baytı aşarsa sessizce kesme, hata say.
  - `TEL,<seq>,<scn>,<tick_ms>`
  - `BTN,<event_id>,<scn>,PRESSED`
- UartTxTask kuyruktan aldığı mesajı kendi statik tamponuna kopyalar. Tampon TC gelene kadar değiştirilmez.

## Zaman damgaları

| | Nerede |
|---|---|
| t₀ | `HAL_GPIO_EXTI_Callback` ilk satırı (filtre kabul ederse kayda geçer) |
| t₁ | ButtonTask'ta `xQueueReceive` döndükten hemen sonra |
| t₂ | ButtonTask'ta yanıt için `xQueueSend` çağrısından hemen önce |
| t₃ | UartTxTask'ta `HAL_UART_Transmit_IT` çağrısından hemen önce |
| t₄ | `HAL_UART_TxCpltCallback` içinde (IT modunda TC kesmesiyle çağrılır) |

- Tümü `timer_us()` (= `TIM2->CNT`) ile alınır. Farklar `uint32_t` çıkarmasıyla (mod 2³²) hesaplanır.
- Kayıtlar olay kimliğiyle eşleşir; tek bir global timestamp değişkeni kullanma.

## Olay kaydı ve durumlar

- RAM'de en az 64 kayıt: `{event_id, t0..t4, geçerlilik bayrakları, status}`. Kapasite aşılırsa `log_overflow++`.
- Durumlar: `ok`, `btn_drop` (buton kuyruğu dolu), `tx_drop` (TX kuyruğu dolu), `tx_error` (UART başlatılamadı), `timeout` (1 s içinde TC gelmedi).
- Alınmamış damga 0 yazılmaz; bayrakla işaretlenir ve aktarımda boş alan olarak gönderilir.
- Sayaçlar: `bounce_rejected`, `btn_drop`, `tx_drop_tel`, `tx_drop_btn`, `tx_error`, `timeout`, `log_overflow`, ölçülen telemetri periyodu min/max, ölçülen CPU işi süresi min/max, görev yığını high-water mark değerleri.

## UartTxTask akışı

1. `xQueueReceive(txQ, &msg, portMAX_DELAY)`
2. Mesaj CMD ise komutu işle; değilse statik tampona kopyala.
3. BTN ise t₃'ü kaydet. `HAL_UART_Transmit_IT` çağır; `HAL_OK` dönmezse `tx_error` işaretle ve devam et.
4. `ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(1000))`. 0 dönerse `HAL_UART_AbortTransmit` çağır ve `timeout` işaretle.
5. TC callback'i: mesaj BTN ise t₄'ü kaydet, sonra `vTaskNotifyGiveFromISR` ve `portYIELD_FROM_ISR`.

## Senaryolar ve komutlar (önerilen tasarım)

Dördüncü görev eklememek ve UART'ın tek sahibini korumak için komutlar UartTxTask'ta işlenir:

- RX: `HAL_UART_Receive_IT` ile bayt bayt okunur. `\n` gelince RX callback'i satırı CMD tipli bir `TxMsg` olarak TX kuyruğuna koyar (`xQueueSendFromISR`).
- `SCN,Sx` → senaryoyu ayarla, kayıtları ve sayaçları sıfırla, TelemetryTask'ı uyandır.
- `STOP` → telemetriyi kapat.
- `DUMP` → yalnızca STOP sonrasında: CSV başlığı, olay satırları, `CNT,...` sayaç satırı ve `END` gönderilir. Bu satırlar 64 bayt kuralına tabi değildir.

Olay satırı biçimi: `scenario,event_id,t0_us,t1_us,t2_us,t3_us,t4_us,status`

## TelemetryTask

| Senaryo | Periyot | CPU işi |
|---|---|---|
| S0 | kapalı | yok |
| S1 | 100 ms | yok |
| S2 | 20 ms | yok |
| S3 | 10 ms | yok |
| S4 | 10 ms | ≈ 2 ms |
| S5 | 10 ms | ≈ 5 ms |

- Periyot `xTaskDelayUntil` ile tutulur. S0'da görev `ulTaskNotifyTake(pdTRUE, portMAX_DELAY)` ile bloklanır; uyanınca `last = xTaskGetTickCount()` yapılır.
- CPU işi: sabit iterasyonlu, sonucu `volatile` bir global değişkene yazılan tamsayı hesabı (ör. CRC32 veya LCG). Kesmeleri kapatma, `vTaskDelay` kullanma. İterasyon sayısı `timer_us()` ile kalibre edilir; her çalışmada gerçek süre ölçülüp sayaçlara yazılır.
- TX kuyruğuna 0 beklemeyle gönderilir; kuyruk doluysa `tx_drop_tel++`.

## ButtonTask

`xQueueReceive(buttonQ, &e, portMAX_DELAY)` → t₁ → BTN mesajını üret → t₂ → `xQueueSend(txQ, &m, 0)`. Gönderim başarısızsa `tx_drop`.

## FreeRTOS ayarları

`configUSE_PREEMPTION 1`, `configTICK_RATE_HZ 1000`, `configCHECK_FOR_STACK_OVERFLOW 2`, `configUSE_MALLOC_FAILED_HOOK 1`. Hook'larda LD1'i yak ve dur.

## PC tarafı

- `interface/`: Python 3, `pyserial`, `tkinter`, `matplotlib`. Arayüz ölçüme karışmaz: veriyi okur, komut gönderir, CSV kaydeder.
- `analysis/`: ham CSV → `measurements/summary.csv` ve iki grafik. Grafikler yalnızca bu betikle üretilir.
- Bağımlılıklar sürümleriyle birlikte `requirements.txt` içinde tutulur.
