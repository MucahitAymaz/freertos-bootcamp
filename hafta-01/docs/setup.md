# Kurulum

CubeMX ayarlarının adım adım listesi için bkz. [gelistirme-plani.md → Adım 1](gelistirme-plani.md#adım-1--cubemx-yapılandırması-ve-iskelet--featurefreertos-iskelet).

Bu belge, sistemi sıfırdan kurup ölçümü tekrar üretebilmek için gereken donanım, yazılım ve yapılandırma adımlarını içerir.

## 1. Donanım

| Bileşen | Değer |
|---|---|
| Kart | NUCLEO-L476RG |
| Bağlantı | Tek USB kablosu (ST-LINK): güç, programlama ve sanal COM portu |
| UART | USART2, PA2 (TX), PA3 (RX). Kart üzerindeki solder bridge'ler üzerinden ST-LINK sanal COM portuna bağlı; harici kablo gerekmez |
| Buton | B1 (mavi), PC13, basınca LOW, düşen kenar. GPIO'da dahili pull-up açık |
| LED | LD2 (yeşil), PA5. Normalde sönük; `Error_Handler`, stack overflow ya da malloc hook tetiklenirse sabit yanar |
| Ek donanım | Yok. Harici USB-UART dönüştürücü kullanılmadı (Arduino D0/D1 pinleri varsayılan olarak USART2'ye bağlı değil) |

## 2. Yazılım Araçları

| Araç | Sürüm |
|---|---|
| STM32CubeIDE | 2.1.1 (GNU Tools for STM32 14.3.rel1) |
| STM32CubeMX | 6.18.1 |
| STM32CubeL4 paketi | FW_L4 V1.18.2 |
| FreeRTOS | V10.3.1 (CubeMX arayüzü CMSIS_V2, uygulama görevleri doğrudan FreeRTOS API'siyle) |
| PC arayüzü çalışma ortamı | Python 3.12.10, tkinter, Windows 11 Pro |
| Arayüz bağımlılıkları | pyserial 3.5, matplotlib 3.11.2, numpy 2.3.5 ([requirements.txt](../interface/requirements.txt)) |

## 3. CubeMX Yapılandırması

Proje Board Selector ile NUCLEO-L476RG seçilerek oluşturuldu. **BSP bileşeni kapatıldı.** Açık kalırsa BSP buton ve LED'i sahiplenir, EXTI önceliğini 15 yapar ve HAL EXTI driver'ı üzerinden `HAL_GPIO_EXTI_Callback`'i atlar.

### 3.1 Saat
- Kaynak: HSI16 → PLL (M = 1, N = 10, R = 2). HSE kullanılmıyor, Nucleo'da X3 kristali takılı değil
- SYSCLK = HCLK = **80 MHz**, Flash latency 4, voltage scale 1
- APB1 / APB2 bölücü 1 → **APB1 / APB2 timer saatleri 80 MHz**
- Flash ART: prefetch, instruction cache ve data cache açık

### 3.2 Zaman damgası timer'ı
- Timer: **TIM2** (32-bit), Internal Clock, kesme yok
- Prescaler **79** / Period **4294967295** → **1 µs** çözünürlük (1 MHz)
- Taşma süresi: 2³² µs ≈ **71,6 dakika**
- HAL timebase: **TIM6**, çünkü SysTick FreeRTOS'a ait

### 3.3 UART
- USART2, Asynchronous, **115200 · 8N1**, oversampling 16
- Mod: **IT** (DMA yok). TX: `HAL_UART_Transmit_IT` + TC callback. RX: bayt bayt `HAL_UART_Receive_IT`
- NVIC önceliği: **6**, "Uses FreeRTOS functions" ✔

### 3.4 Buton (EXTI)
- PC13 → GPIO_EXTI13, **düşen kenar**, pull-up, User Label `B1`
- NVIC: `EXTI15_10_IRQn`, önceliği **5**, "Uses FreeRTOS functions" ✔
- NVIC → Code generation: EXTI line[15:10] için "Generate IRQ handler" ve "Call HAL handler" ✔ (klasik `HAL_GPIO_EXTI_IRQHandler(B1_Pin)` yolu)

### 3.5 FreeRTOS
- Arayüz: **CMSIS_V2**. Uygulama görevleri `xTaskCreate` ile oluşturuluyor; CubeMX'in `defaultTask`'ı ilk satırında `vTaskDelete(NULL)` çağırıyor
- `configUSE_PREEMPTION` = 1, `configTICK_RATE_HZ` = **1000**, `configMAX_PRIORITIES` = 56
- `configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY` = **5**
- `configCHECK_FOR_STACK_OVERFLOW` = 2, `configUSE_MALLOC_FAILED_HOOK` = 1, `configUSE_NEWLIB_REENTRANT` = 1
- Heap: heap_4, `configTOTAL_HEAP_SIZE` = 32768
- `INCLUDE_vTaskDelayUntil` = 1, `INCLUDE_uxTaskGetStackHighWaterMark` = 1
- HAL timebase: **TIM6** (öncelik 15)

## 4. Firmware Derleme ve Yükleme

1. STM32CubeIDE'yi **repo dışında** bir workspace klasörüyle aç (ör. `C:\Users\<kullanıcı>\STM32CubeIDE\workspace_bootcamp`). Workspace, proje klasörünün (`hafta-01/firmware`) içinde olursa Eclipse projeyi içe aktarmaz.
2. *File → Import → General → Existing Projects into Workspace* → root directory olarak `hafta-01/firmware` klasörünü seç. **"Copy projects into workspace" işaretsiz** olmalı, yoksa IDE repodaki dosyalar yerine bir kopyayla çalışır.
3. Projeye sağ tık → *Refresh*, ardından *Project → Build Project* (Debug yapılandırması, `-O0 -g3`). Beklenen: 0 hata, 0 uyarı.
4. Kartı USB ile bağla ve *Run → Debug As → STM32 C/C++ Application* ile yükle. Program `main()`'de durursa *Resume (F8)*.
5. Ölçümler `olcum-v2` tag'indeki firmware ile alındı: `git checkout olcum-v2` ile aynı kod elde edilir.

CubeMX'te bir ayar değiştirip kodu yeniden ürettikten sonra CubeMX'teki *Open Project* düğmesini kullanma. Bu düğme CubeIDE'yi proje klasörünü workspace yaparak açar. CubeIDE'de projeye sağ tıklayıp *Refresh* demek yeterli.

## 5. PC Arayüzünü Çalıştırma

1. Bağımlılıkları kur (Python 3.12 ile denendi):
   ```bash
   python -m pip install -r hafta-01/interface/requirements.txt
   ```
2. Arayüzü başlat:
   ```bash
   python hafta-01/interface/app.py
   ```
3. Port listesinden **STLink Virtual COM Port**'u seç ve **Bağlan**'a bas. Port aynı anda tek programa açılabildiği için Tera Term gibi başka bir terminal kapalı olmalı.
4. Bir senaryo düğmesine (S0–S5) bas. Isınma sayacı 5 s'yi doldurunca butona bas. **STOP + DUMP** ile kayıtlar `measurements/Sx.csv` ve `measurements/Sx_counters.csv` dosyalarına olduğu gibi yazılır.

Arayüz yalnızca gözlemler: satırları okur, komut gönderir ve DUMP çıktısını değiştirmeden kaydeder. PC saati yalnızca gösterim için (TEL/s grafiği, 0,5 s basış uyarısı) kullanılır. "Ham oturum kaydı" işaretliyse bütün satırlar `interface/logs/` altına da yazılır. Bu klasör git'e girmez.

## 6. Ölçüm Alma

Senaryo adımları için bkz. [README → Ölçüm adımları](../README.md#42-ölçüm-adımları-her-senaryoda-aynı-sıra).

Kayıtların dışarı aktarılması:

1. Senaryo çalışırken kart her olayı RAM'deki kayıt tablosuna yazar (en fazla 64 olay). Ölçüm sırasında seri porttan yalnızca TEL ve BTN satırları gelir.
2. Arayüzde **STOP + DUMP** düğmesi önce `STOP` gönderir: telemetri durur ve kuyrukta kalan mesajlar gönderilir. Ardından `DUMP` gönderilir.
3. Kart şu satırları gönderir: CSV başlığı, her olay için `scenario,event_id,t0_us,t1_us,t2_us,t3_us,t4_us,status`, `CNT,...` sayaç satırı ve `END`.
4. Arayüz `END` gelince başlığı ve olay satırlarını **olduğu gibi** `measurements/Sx.csv` dosyasına, sayaçları `measurements/Sx_counters.csv` dosyasına yazar. Aynı isimde bir dosya varsa üzerine yazmadan önce sorar.
5. Analiz: `python hafta-01/analysis/analyze.py` → `measurements/summary.csv`, `analysis/plots/*.png` ve `analysis/tables.md`.

Arayüz olmadan da ölçüm yapılabilir: herhangi bir seri terminalde (115200 8N1, gönderme CR) `SCN,S3`, `STOP`, `DUMP` yazılıp DUMP çıktısı elle kaydedilebilir. Bu durumda terminalin local echo ayarı kapalı olmalı, yoksa yazılan komut karakterleri satırların arasına karışır.
