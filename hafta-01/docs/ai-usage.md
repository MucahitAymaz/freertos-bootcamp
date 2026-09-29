# Yapay Zekâ Kullanımı

> Bu belge, çalışma oturumlarında gerçekten olanlar esas alınarak Claude Code ile birlikte hazırlandı ve tarafımdan gözden geçirildi.

## Kullanılan araçlar

- **Claude (sohbet):** ödev gereksinimlerinin yorumlanması, README ve belge iskeletlerinin hazırlanması, Git/GitHub iş akışı.
- **Claude Code:** firmware (FreeRTOS görevleri, ISR'ler, UART zinciri, olay kaydı), PC arayüzü, analiz betiği, rapor ve belge taslakları, CubeMX çıktısının kontrolü ve hata ayıklama. Kod adım adım yazıldı. Her adımdan sonra kartta doğruladım ve doğrulamadan bir sonraki adıma geçmedik.

## Hangi işlerde destek alındı?

| İş | Destek | Not |
|---|---|---|
| Belge iskeletleri (README, docs/) | Evet | İçerik ölçümler ve kod ilerledikçe dolduruldu |
| Firmware | Evet | `app_config.h` ve `app_time.h`'yi yönlendirmeyle kendim yazdım. Zaman kısıtı nedeniyle diğer app dosyalarını Claude Code yazdı, ben okuyup kartta doğruladım. CubeMX yapılandırmasını kendim yaptım |
| PC arayüzü | Evet | Claude Code yazdı. Kartla test ettim, grafik düzenini değiştirdim (aşağıda) |
| Analiz ve grafik betikleri | Evet | Claude Code yazdı. Tablolar ve grafikler yalnızca betik çıktısından geliyor |
| Hata ayıklama | Evet | CubeIDE workspace hatası, BSP çakışması, `H_EXTI_13` derleme hatası, seri port seçimi |
| Ölçüm | Hayır | Bütün ölçümleri gerçek kartta ben yaptım. Claude Code yalnızca prosedürü anlattı ve veri bütünlüğünü kontrol etti |

## Adım kayıtları (Claude Code)

| Adım | Destek verilen iş | Değişen dosyalar | Nasıl doğrulandı | Hangi öneri değiştirildi |
|---|---|---|---|---|
| Kart değişikliği (F746 → NUCLEO-L476RG) | Donanım tablosu, CubeMX adımları ve belgelerin L476RG'ye uyarlanması | `CLAUDE.md`, `README.md`, `docs/gelistirme-plani.md`, `docs/setup.md` | Pinleri (PA2/PA3, PC13, PA5) kartın kullanıcı kılavuzuyla karşılaştırdım | — |
| Adım 1: CubeMX çıktısının kontrolü ve iskelet | Üretilen kodun donanım tablosuyla karşılaştırılması (BSP, TIM2 PSC, EXTI hataları bulundu), `.gitignore`, `app_config.h` ve `app_time.h` iskeleti kullanıcıyla birlikte, görev iskeletleri, `app_start()`, hook'lar | `firmware/.gitignore`, `Core/Inc/app_config.h`, `app_time.h`, `app_main.h`, `Core/Src/app_time.c`, `app_main.c`, `app_telemetry.c`, `app_button.c`, `app_uart.c`, `freertos.c` ve `main.c` (USER CODE blokları) | Sıfır hatayla derlendi. LD2'nin yanıp söndüğünü gördüm. Live Expressions'ta TIM2 sayacının arttığını izledim | CubeMX'te BSP'yi kapattım, TIM2 prescaler'ını düzelttim, EXTI kesmesini yeniden açtım (üretilen kod bu üç noktada tabloyla uyuşmuyordu) |
| Adım 2: UART TX zinciri | TX kuyruğu, `TxMsg`, 64 bayt biçimleme, UartTxTask (IT gönderim, task notification, 1 s timeout), TC callback'inde t4, geçici test üreticisi | `Core/Inc/app_config.h`, `app_main.h`, `app_uart.h`, `Core/Src/app_main.c`, `app_uart.c`, `app_telemetry.c` | Terminalde t₄ − t₃ = 5559–5560 µs gördüm (teorik 5556 µs). Timer ve TC mantığı böylece doğrulandı. Satırların sabit uzunlukta olduğunu terminaldeki kayma deseninden gördüm | Harici USB-TTL yerine ST-LINK sanal COM portunu kullandım |
| Adım 3: Buton zinciri, olay kaydı, DUMP | EXTI callback (t0, 30 ms filtre, `xQueueSendFromISR`), buton kuyruğu, ButtonTask (t1, t2), olay kaydı ve sayaçlar, RX satır okuma, DUMP komutu, UART hata callback'i | `Core/Inc/app_config.h`, `app_main.h`, `app_uart.h`, `app_button.h`, `app_eventlog.h`, `Core/Src/app_main.c`, `app_button.c`, `app_uart.c`, `app_eventlog.c`, `app_telemetry.c` | 25 basışta 25 BTN satırı geldi, hepsi `ok`. DUMP'ta R ≈ 5,68 ms, diğer aşamalar onlarca µs çıktı | 30 ms filtrenin kartın RC filtresiyle birlikte gereksiz olup olmadığını sordum. Filtrenin gecikme eklemeyen bir kilitleme olduğunu öğrendim ve değiştirmedik |
| Adım 4: Telemetri, senaryolar, CPU işi | Senaryo tablosu, TelemetryTask (`vTaskDelayUntil`, S0'da bildirimle bekleme), LCG tabanlı CPU işi ve TIM2 ile kalibrasyon, SCN/STOP komutları, DUMP'ın STOP'a bağlanması, periyot/iş süresi min-max ve yığın high-water mark sayaçları. FreeRTOS V10.3.1'de `xTaskDelayUntil` olmadığı için `vTaskDelayUntil` kullanıldı | `Core/Inc/app_config.h`, `app_eventlog.h`, `app_button.h`, `app_main.h`, `app_telemetry.h`, `Core/Src/app_telemetry.c`, `app_uart.c`, `app_main.c`, `app_button.c`, `app_eventlog.c` | Beş senaryoyu Tera Term log'uyla çalıştırdım. Periyotlar 100/20/10 ms, CPU işi 2002 ve 5003–5052 µs, TEL sıra numaralarında boşluk yok | — |
| Adım 5: PC arayüzü | Protokol ayrıştırıcı, ayrı thread'de seri port okuyucu, tkinter + matplotlib arayüzü (canlı akış, R, aşamalar, dağılım, senaryo karşılaştırma grafikleri, ölçüm prosedürü yardımcıları, DUMP'ın `measurements/` altına değiştirilmeden kaydı), kuru deneme log'uyla çevrimdışı grafik testi | `interface/app.py`, `protocol.py`, `serial_link.py`, `plots.py`, `requirements.txt`, `.gitignore`, `docs/setup.md` | Arayüzü kartla çalıştırdım: bağlantı, senaryo komutları, buton bildirimi, DUMP ve grafikler | Aşama grafiklerini dikeyden yataya çevirttim; zaman soldan sağa aktığı için okunması daha kolay |
| Adım 6: README tabloları ve tag | Araç sürümleri, derleme ve FreeRTOS ayar tablolarının proje dosyalarından doldurulması, `olcum-v1` tag'i | `README.md`, `firmware/.gitignore` | Değerleri CubeIDE ve CubeMX'teki ayarlarla karşılaştırdım | — |
| Adım 7: Ölçüm | Ölçüm prosedürünün anlatılması, eksik S3'ün tespiti, veri bütünlüğü kontrolü (ölçümü kullanıcı yaptı) | `measurements/S0–S5.csv`, `S0–S5_counters.csv` (arayüz tarafından kaydedildi) | Olay sayıları, kimlik sürekliliği ve sayaçlar kontrol edildi | İlk turda atlanan S3'ü ayrıca ölçtüm |
| Şartname kontrolü ve olcum-v2 | Ödev şartnamesinin repo ile karşılaştırılması; eksik bulunan kuyruk yüksek su seviyesi için firmware'e HWM sayaçları, `olcum-v2` tag'i, v1 ölçümlerinin arşivlenmesi, S2'nin 0,5 s kuralı nedeniyle tekrar ölçülmesinin önerilmesi, basış aralığı kontrolünün betiğe eklenmesi. Önceki rapordaki "DMA sorunu çözer" önerisi düzeltildi (DMA ancak ISR'den zincirlenirse işe yarar) | `firmware/Core/Src/app_button.c`, `app_telemetry.c`, `app_uart.c`, `Core/Inc/app_eventlog.h`, `measurements/olcum-v1/`, `analysis/analyze.py`, `analysis/report.md` | Yeni firmware'i S5'te 5 basışla denedim (`txq_hwm = 7`, `btnq_hwm = 1`). Altı senaryoyu yeniden ölçtüm. S2'yi kısa basış aralıkları yüzünden tekrarladım | Şartnameyi Claude'a gösterip eksikleri kontrol ettirdim. Kısa yol (eksikliği sınırlarda yazmak) yerine firmware'i değiştirip yeniden ölçmeyi seçtim. DMA ile ilgili sorum, rapordaki yanlış önerinin düzeltilmesini sağladı |
| Adım 8: Analiz ve rapor | Analiz betiği (özet tablo, iki grafik, rapor tabloları, ek gözlemler, dışlanan kayıtlar). Rapordaki tabloların betik çıktısından doldurulması. Bulgular ve değerlendirme bölümlerinin taslağı (kullanıcı gözden geçirecek) | `analysis/analyze.py`, `analysis/tables.md`, `analysis/plots/*.png`, `analysis/report.md`, `measurements/summary.csv`, `README.md` | Rapordaki sayıları `tables.md` çıktısıyla karşılaştırdım | Değerlendirme bölümünü madde listesinden anlatıma çevirttim. Ödevde "CPU hızı" mı "CPU yükü" mü istendiğini şartnameden kontrol ettirdim (yük) |

## Üretilen kod nasıl kontrol edildi?

- **Derleme:** Her adımda CubeIDE'de sıfır hata ve sıfır uyarıyla derlendi. Claude Code dosyaları ayrıca `arm-none-eabi-gcc -Wall -Wextra` ile kontrol etti.
- **Kartta adım adım test:** Hiçbir adım kartta doğrulanmadan bir sonrakine geçilmedi. LED testi, t₄ − t₃ ≈ 5559 µs, her basışta tek BTN satırı, periyot ve iş süresi sayaçları, kuyruk sayaçları.
- **Ölçüm zincirinin kendi kendini doğrulaması:** Fiziksel hat süresinin (5,556 ms) ölçümde 5,559 ms çıkması, timer'ın ve TC mantığının doğru olduğunu gösterdi. Periyotlar ve CPU işi, varsayılmak yerine kartta ölçüldü.
- **Kuru deneme:** Ölçümden önce S0 ve S5'te 10'ar basışla denendi. S5'teki birikim burada fark edildi ve nedeni ölçümden önce açıklandı.
- **Veri kontrolü:** Olay kimliklerinin sürekliliği, 64 bayt satır uzunluğu (arayüz sayacı), basış aralıkları (kartın t₀ damgalarından) ve sayaç tutarlılığı kontrol edildi.
- **Şartname kontrolü:** Teslimden önce repo, ödev şartnamesiyle madde madde karşılaştırıldı. Eksik bulunan kuyruk seviyesi ölçümü için firmware güncellenip bütün senaryolar yeniden ölçüldü.
- Lojik analizör kullanılmadı.

## Hangi öneriler değiştirildi ve neden?

| Öneri | Değişiklik | Neden |
|---|---|---|
| CubeMX'in ürettiği kodu olduğu gibi kullanmak | BSP kapatıldı, TIM2 prescaler 0 → 79, EXTI kesmesi yeniden açıldı | Üretilen kod donanım tablosuyla karşılaştırıldığında üç hata çıktı. Olduğu gibi kalsaydı zaman damgaları 80 kat yanlış çıkacak, buton önceliği 15 olacaktı |
| Harici USB-TTL dönüştürücüyle seri bağlantı | ST-LINK sanal COM portu kullanıldı | Kartta USART2 varsayılan olarak ST-LINK'e bağlı, Arduino pinlerine değil |
| Aşama grafiklerinin dikey yığılmış çubuk olması | Yatay yığılmış çubuk (zaman çizelgesi) | Zaman soldan sağa aktığında t₀ → t₄ akışı ve 20 ms çizgisi daha kolay okunuyor |
| Kuyruk seviyesini ölçmeden raporda sınırlılık olarak yazmak | Firmware'e HWM sayaçları eklendi, `olcum-v2` ile yeniden ölçüldü | Şartname özet tabloda kuyruk yüksek su seviyesini istiyor. Ayrıca raporun ana iddiası (S5'te kuyruk doluyor) böylece doğrudan ölçüme dayandı |
| S2 ölçümünü olduğu gibi kullanmak | S2 tekrar ölçüldü | 4 basış 0,5 s kuralının altında kalmıştı (0,45 s) |
| "DMA sorunu çözer" önerisi | "DMA ancak aktarımlar TC kesmesinden zincirlenirse çözer" olarak düzeltildi | Sorunun kaynağı gönderimi başlatma kararının en düşük öncelikli göreve bağlı olması. DMA tek başına bunu değiştirmez |
| Firmware'i S5'teki birikimi giderecek şekilde değiştirmek | Değiştirilmedi, raporda öneri olarak tartışıldı | Görev öncelikleri şartnamede sabit. Birikim, ölçülmesi istenen etkinin kendisi |

## Beyan

Ölçüm sonuçları gerçek kart üzerinde alınmıştır; sentetik veri gerçek sonuç olarak sunulmamıştır.
