# Kod Notları

Kritik kod blokları ve çalışma biçimleri. Her bölümde ilgili kaynak dosyadan kısa bir kod bloğu ve açıklaması yer alır.

> Kod blokları gerçek kaynak dosyalardan alınmalıdır; yalnızca ekran görüntüsü kullanılmaz.

## 1. Buton ISR ve 30 ms Filtre

Kaynak: _TBD: dosya ve fonksiyon_

```c
// TBD
```

Açıklanacaklar:
- t₀'ın ISR girişinde, hangi timer'dan alındığı
- Kabul edilen kenar ve 30 ms içindeki tekrar kenarların sayılması
- Olay kimliğinin üretilmesi ve kuyruğa `xQueueSendFromISR` ile gönderilmesi
- Kuyruk doluysa kayıp sayacının artırılması
- `portYIELD_FROM_ISR` kullanımı
- IRQ önceliğinin FreeRTOS API çağrısına uygun olması

## 2. TelemetryTask (öncelik 3)

Kaynak: _TBD_

```c
// TBD
```

Açıklanacaklar:
- `xTaskDelayUntil` ile periyot (10 / 20 / 100 ms) ve tick dönüşümü
- Kapalı senaryoda (S0) görevin bloklanması
- Ek CPU işi (S4: ≈2 ms, S5: ≈5 ms): hangi işlem, kalibrasyon, optimizasyonla silinmemesi
- 64 baytlık TEL mesajının üretilmesi
- TX kuyruğu doluysa kayıp sayacı

## 3. ButtonTask (öncelik 2)

Kaynak: _TBD_

```c
// TBD
```

Açıklanacaklar:
- `xQueueReceive` sonrası t₁ kaydı
- 64 baytlık BTN yanıtının olay kimliğiyle üretilmesi
- `xQueueSend` öncesi t₂ kaydı
- Gönderim başarısızsa olayın `drop` olarak işaretlenmesi

## 4. UartTxTask (öncelik 1) ve TC Tamamlanması

Kaynak: _TBD_

```c
// TBD
```

Açıklanacaklar:
- UART başlatma çağrısından hemen önce t₃ kaydı
- Başlatma başarısızsa `tx_error`, sonsuz bekleme yok
- TC callback'inde t₄ kaydı ve görevin uyandırılması
- Tamponun aktarım bitene kadar geçerli kalması
- "DMA bitti" ile "son bit çıktı" farkı
- Timeout (1 s) durumunda olayın güvenle sonlandırılması

## 5. Olay Kayıtları

Kaynak: _TBD_

```c
// TBD
```

Açıklanacaklar:
- Kayıt yapısı (event_id, t₀–t₄, status)
- En az 64 olaylık RAM tamponu ve taşma sayacı
- Kayıtların olay kimliğiyle eşleştirilmesi (tek global timestamp kullanılmaması)
- Deney sonunda dışarı aktarma

## 6. Zaman Hesapları

- Timer çözünürlüğü ve taşma süresi: _TBD_
- Farkların uint32 üzerinde mod 2³² hesaplanması
- Eksik zamanların boş bırakılması

## 7. Mesaj Biçimi

| Tür | Örnek içerik | Boyut |
|---|---|---|
| TEL | _TBD_ | 64 bayt (63 + LF) |
| BTN | _TBD_ | 64 bayt (63 + LF) |
| Kayıt aktarımı | _TBD_ | _TBD_ |
