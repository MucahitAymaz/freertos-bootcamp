# FreeRTOS Bootcamp — Çalışma Kuralları

Bu repo FreeRTOS Bootcamp'in haftalık ödevlerini içerir. Her hafta kendi klasöründedir (`hafta-01/`, `hafta-02/`, ...). Haftaya özel teknik tarif o klasördeki `CLAUDE.md` dosyasındadır. O haftanın dosyalarında çalışmadan önce onu oku.

## Kullanıcı

- Gömülü sistemler mühendisi. STM32 HAL, CubeMX ve CubeIDE'yi biliyor; FreeRTOS'u bu bootcamp'te öğreniyor.
- Yanıtlar Türkçe olsun. Teknik terimler (queue, ISR, preemption, tick) İngilizce kalabilir.
- Kod içi yorumlar İngilizce ve yalnızca ASCII karakter olsun (derleyici/encoding sorunlarını önlemek için).

## Öğretme modu (her adımda uygula)

1. Koda başlamadan önce 3–6 cümleyle anlat: bu adımda ne yapacağız, hangi RTOS kavramını kullanıyoruz ve neden bu yolu seçtik.
2. Küçük adımlarla ilerle. Bir seferde planın tek bir adımını uygula; birden fazla adımı birleştirme.
3. Bir FreeRTOS API'sini ilk kez kullandığında 1–2 cümleyle açıkla: ne yapar, neden bu API (ör. neden `xQueueSendFromISR`, `portYIELD_FROM_ISR` ne işe yarar, `xTaskDelayUntil` ile `vTaskDelay` farkı).
4. Adımı bir "Kartta nasıl doğrularım?" listesiyle bitir: ne gözlenmeli, hangi değer beklenmeli, beklenen çıkmazsa ilk nereye bakılmalı.
5. Kullanıcı kartta doğrulayıp onay vermeden sonraki adıma geçme.
6. Bilmediğin donanım ayrıntısını tahmin etme. Datasheet, reference manual veya kartın kullanıcı kılavuzunda nereye bakılacağını söyle.

## Değişmez kurallar

- **Veri uydurma.** `measurements/` klasörüne yalnızca karttan gelen gerçek veri girer. Test için sentetik veri gerekirse adında `synthetic` geçen ayrı bir dosyaya yaz ve gerçek sonuç gibi sunma.
- **CubeMX dosyası (`.ioc`) düzenlenmez.** Gereken CubeMX ayarını kullanıcıya adım adım söyle; ayarı kullanıcı yapar ve kodu yeniden üretir.
- CubeMX'in ürettiği dosyalarda yalnızca `/* USER CODE BEGIN ... */` ile `/* USER CODE END ... */` arasına yaz. Bu blokların dışındaki değişiklikler yeniden üretimde silinir.
- Karta yükleme (flash) her zaman kullanıcı tarafından yapılır.

## Git

- `main`'e doğrudan commit atma. Her iş kendi branch'inde olsun: `feature/...`, `analysis/...`, `docs/...`.
- Küçük ve anlamlı commit'ler. Commit mesajı Türkçe, ilk satır en fazla 72 karakter.
- Push, merge ve tag işlemlerini kullanıcıya sormadan yapma.
- Ölçümlerden önce firmware bir tag ile dondurulur (ör. `olcum-v1`). Bu tag'den sonra firmware değişirse kullanıcıyı açıkça uyar: eski ölçümler yeni kodu temsil etmez.

## AI kullanım kaydı

Her adımın sonunda ilgili haftanın `docs/ai-usage.md` dosyasına kısa bir satır ekle: hangi işte destek verildi, hangi dosyalar değişti. "Nasıl doğrulandı" ve "hangi öneri değiştirildi" kısımlarını kullanıcı doldurur; oraya `(kullanıcı dolduracak)` yaz.
