# Yapay Zekâ Kullanımı

## Kullanılan araçlar

- Claude (sohbet): ödev gereksinimlerinin yorumlanması, README ve belge iskeletlerinin hazırlanması, Git/GitHub iş akışı
- Claude Code: _TBD: hangi işlerde kullanıldığı_

## Hangi işlerde destek alındı?

| İş | Destek | Not |
|---|---|---|
| Belge iskeletleri (README, docs/) | Evet | İçerik ölçümler ve kod ilerledikçe dolduruldu |
| Firmware | _TBD_ | |
| PC arayüzü | _TBD_ | |
| Analiz ve grafik betikleri | _TBD_ | |
| Hata ayıklama | _TBD_ | |

## Adım kayıtları (Claude Code)

| Adım | Destek verilen iş | Değişen dosyalar | Nasıl doğrulandı | Hangi öneri değiştirildi |
|---|---|---|---|---|
| Kart değişikliği (F746 → NUCLEO-L476RG) | Donanım tablosu, CubeMX adımları ve belgelerin L476RG'ye uyarlanması | `CLAUDE.md`, `README.md`, `docs/gelistirme-plani.md`, `docs/setup.md` | (kullanıcı dolduracak) | (kullanıcı dolduracak) |
| Adım 1: CubeMX çıktısının kontrolü ve iskelet | Üretilen kodun donanım tablosuyla karşılaştırılması (BSP, TIM2 PSC, EXTI hataları bulundu), `.gitignore`, `app_config.h` ve `app_time.h` iskeleti kullanıcıyla birlikte, görev iskeletleri, `app_start()`, hook'lar | `firmware/.gitignore`, `Core/Inc/app_config.h`, `app_time.h`, `app_main.h`, `Core/Src/app_time.c`, `app_main.c`, `app_telemetry.c`, `app_button.c`, `app_uart.c`, `freertos.c` ve `main.c` (USER CODE blokları) | (kullanıcı dolduracak) | (kullanıcı dolduracak) |
| Adım 2: UART TX zinciri | TX kuyruğu, `TxMsg`, 64 bayt biçimleme, UartTxTask (IT gönderim, task notification, 1 s timeout), TC callback'inde t4, geçici test üreticisi | `Core/Inc/app_config.h`, `app_main.h`, `app_uart.h`, `Core/Src/app_main.c`, `app_uart.c`, `app_telemetry.c` | (kullanıcı dolduracak) | (kullanıcı dolduracak) |
| Adım 3: Buton zinciri, olay kaydı, DUMP | EXTI callback (t0, 30 ms filtre, `xQueueSendFromISR`), buton kuyruğu, ButtonTask (t1, t2), olay kaydı ve sayaçlar, RX satır okuma, DUMP komutu, UART hata callback'i | `Core/Inc/app_config.h`, `app_main.h`, `app_uart.h`, `app_button.h`, `app_eventlog.h`, `Core/Src/app_main.c`, `app_button.c`, `app_uart.c`, `app_eventlog.c`, `app_telemetry.c` | (kullanıcı dolduracak) | (kullanıcı dolduracak) |

## Üretilen kod nasıl kontrol edildi?

_TBD: kod incelemesi, derleme uyarıları, kart üzerinde test, timer ile periyot doğrulama, lojik analizör vb._

## Hangi öneriler değiştirildi ve neden?

| Öneri | Değişiklik | Neden |
|---|---|---|
| _TBD_ | _TBD_ | _TBD_ |

## Beyan

Ölçüm sonuçları gerçek kart üzerinde alınmıştır; sentetik veri gerçek sonuç olarak sunulmamıştır.
