# Kurulum

CubeMX ayarlarının adım adım listesi için bkz. [gelistirme-plani.md → Adım 1](gelistirme-plani.md#adım-1--cubemx-yapılandırması-ve-iskelet--featurefreertos-iskelet).

Bu belge, sistemi sıfırdan kurup ölçümü tekrar üretebilmek için gereken donanım, yazılım ve yapılandırma adımlarını içerir.

## 1. Donanım

| Bileşen | Değer |
|---|---|
| Kart | 32F746G-DISCO |
| Bağlantı | USB (ST-LINK): güç, programlama ve sanal COM portu |
| UART | USART1, PA9 (TX), PB7 (RX) |
| Buton | B1 (mavi), PI11, basınca HIGH, dahili pull-down |
| Ek donanım | _TBD: varsa lojik analizör, harici USB-UART vb._ |

## 2. Yazılım Araçları

| Araç | Sürüm |
|---|---|
| STM32CubeIDE | _TBD_ |
| STM32CubeF7 paketi | _TBD_ |
| FreeRTOS | _TBD_ |
| PC arayüzü çalışma ortamı | _TBD_ |
| Arayüz bağımlılıkları | _TBD_ |

## 3. CubeMX Yapılandırması

### 3.1 Saat
- SYSCLK: _TBD_ MHz
- APB1 / APB2 timer saatleri: _TBD_

### 3.2 Zaman damgası timer'ı
- Timer: _TBD_
- Prescaler / period: _TBD_ → _TBD_ µs çözünürlük
- Taşma süresi: _TBD_

### 3.3 UART
- Baud: 115200 · 8N1
- Mod: _TBD: IT / DMA_
- NVIC önceliği: _TBD_

### 3.4 Buton (EXTI)
- Kenar: _TBD: yükselen / düşen_
- NVIC önceliği: _TBD_

### 3.5 FreeRTOS
- Arayüz: _TBD_
- `configTICK_RATE_HZ`: _TBD_
- `configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY`: _TBD_
- HAL timebase: _TBD_

## 4. Firmware Derleme ve Yükleme

1. _TBD_
2. _TBD_
3. _TBD_

## 5. PC Arayüzünü Çalıştırma

1. _TBD: bağımlılıkları kurma_
2. _TBD: arayüzü başlatma_
3. _TBD: port seçimi ve bağlanma_

## 6. Ölçüm Alma

Senaryo adımları için bkz. [README → Ölçüm adımları](../README.md#42-ölçüm-adımları-her-senaryoda-aynı-sıra).

_TBD: kayıtların karttan dışarı aktarılması ve CSV'ye kaydedilmesi._
