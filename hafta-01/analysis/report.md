# Analiz Raporu: Yük Altında Buton Yanıt Süresi

> Tablolardaki ve grafiklerdeki bütün sayılar `analysis/analyze.py` betiğinin `measurements/` altındaki ham CSV dosyalarından ürettiği çıktıdır (bkz. [tables.md](tables.md)). Ham CSV'ler elle düzenlenmemiştir.

## 1. Deney Koşulları

- Kart, MCU saati, tick hızı, timer ve derleme ayarları: bkz. [README](../README.md#1-donanım-bağlantılar-ve-araç-sürümleri)
- Ölçülen firmware: `olcum-v1` tag'i (`9124f34`). NUCLEO-L476RG, 80 MHz, FreeRTOS 10.3.1, Debug `-O0`
- Teslim commit'i: _TBD_
- Ölçüm tarihi: 2026-09-29
- Prosedür: her senaryoda `SCN,Sx` → 5 s ısınma → en az 30 basış (en az 0,5 s aralıklı, düzensiz) → `STOP` → `DUMP`. CSV'ler PC arayüzü tarafından DUMP çıktısından olduğu gibi kaydedildi.

## 2. Özet Tablo

Birim: ms. Kaynak: [measurements/summary.csv](../measurements/summary.csv). R istatistikleri yalnızca başarılı (`ok`) olaylar üzerinden hesaplandı. p95 en yakın sıra yöntemiyle alındı, yani gözlenmiş bir örnektir.

| Senaryo | Kabul edilen olay | Başarılı (ok) | R min | R ort | R medyan | R p95 | R maks (gözlenen) | > 20 ms | drop | tx_error | timeout | Kayıt kaybı |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S0 | 35 | 35 | 5,675 | 5,676 | 5,676 | 5,679 | 5,680 | 0 | 0 | 0 | 0 | 0 |
| S1 | 30 | 30 | 5,675 | 5,837 | 5,676 | 7,783 | 8,325 | 0 | 0 | 0 | 0 | 0 |
| S2 | 30 | 30 | 5,675 | 6,102 | 5,676 | 10,333 | 10,730 | 0 | 0 | 0 | 0 | 0 |
| S3 | 30 | 30 | 5,675 | 7,114 | 6,639 | 9,958 | 10,662 | 0 | 0 | 0 | 0 | 0 |
| S4 | 32 | 32 | 5,675 | 8,178 | 7,350 | 12,773 | 13,011 | 0 | 0 | 0 | 0 | 0 |
| S5 | 30 | 28 | 19,240 | 121,767 | 151,999 | 164,969 | 164,997 | 27 | 2 | 0 | 0 | 0 |

Dışlanan kayıtlar ve nedenleri: S5 olay 17 ve 28, durum `tx_drop` (TX kuyruğu dolu). Bu iki olayda t₃ ve t₄ alınmadı, bu yüzden R hesaplanamaz. Zaman istatistiklerinden dışlandılar ama kabul edilen olay sayısında ve `drop` sütununda yer alıyorlar. "Deadline karşılandı" olarak sayılmadılar. Aynı senaryoda kart ayrıca 14 TEL mesajını da düşürdü (`tx_drop_tel = 14`).

## 3. Aşama Süreleri

Birim: ms, başarılı olayların ortalaması.

| Senaryo | t₁ − t₀ | t₂ − t₁ | t₃ − t₂ | t₄ − t₃ | R |
|---|---|---|---|---|---|
| S0 | 0,024 | 0,037 | 0,056 | 5,559 | 5,676 |
| S1 | 0,025 | 0,037 | 0,215 | 5,559 | 5,837 |
| S2 | 0,024 | 0,037 | 0,481 | 5,559 | 6,102 |
| S3 | 0,024 | 0,039 | 1,492 | 5,559 | 7,114 |
| S4 | 0,167 | 0,038 | 2,414 | 5,559 | 8,178 |
| S5 | 0,698 | 0,038 | 115,472 | 5,559 | 121,767 |

Gözlenen maksimumlar (ms): t₁ − t₀ S3'te 0,027, S4'te 1,775, S5'te 4,438. t₃ − t₂ S1'de 2,701, S2'de 5,106, S3'te 5,038, S4'te 5,640, S5'te 159,369.

Kart sayaçları: telemetri periyodu bütün senaryolarda hedefin ± 3 µs içinde kaldı. CPU işi S4'te 2002–2064 µs, S5'te 5002–5090 µs sürdü. `bounce_rejected` bütün senaryolarda 0.

## 4. Grafikler

### 4.1 Olay numarası → R (20 ms deadline çizgisiyle)
![Olay → R](plots/r_per_event.png)

### 4.2 Senaryo → aşama ortalamaları (yığılmış)
![Senaryo → aşamalar](plots/stage_means.png)

Grafik üretme kodu: [analysis/analyze.py](analyze.py). Çizim fonksiyonları PC arayüzüyle ortak: [interface/plots.py](../interface/plots.py).

## 5. Bulgular

> Not: 5. ve 6. bölümler Claude ile birlikte yazıldı (bkz. [ai-usage.md](../docs/ai-usage.md)). Sayıların hepsi bölüm 2–3'teki betik çıktısından alındı.

### 5.1 Telemetri frekansının etkisi (S0 → S1 → S2 → S3)

Ölçüme başlamadan önceki beklentimiz, telemetri sıklaştıkça BTN yanıtının TX kuyruğunda TEL mesajlarının arkasında kalacağı ve bu yüzden t₃ − t₂'nin uzayacağıydı. İlk dört senaryo bu beklentiyle örtüştü. Üstelik değişim yalnızca o aşamada kaldı. t₃ − t₂ ortalaması S0'da 0,056 ms iken S1'de 0,215, S2'de 0,481, S3'te 1,492 ms oldu. Aynı sürede t₁ − t₀ 0,024–0,025 ms'de, t₂ − t₁ 0,037–0,039 ms'de, hat süresi t₄ − t₃ ise 5,559 ms'de hiç kıpırdamadı.

Bu bekleme her basışta ortaya çıkmıyor. Butona basıldığı anda hatta bir TEL mesajı varsa BTN onun bitmesini bekliyor, yoksa hiç beklemiyor. Bu yüzden t₃ − t₂'nin 1 ms'yi aştığı olay sayısı, hattın ne kadar dolu olduğuyla birlikte arttı: S1'de 2/30, S2'de 4/30, S3'te 15/30. Hat doluluğu ise sırasıyla %5,6, %27,8 ve %55,6. S1 ve S3'teki oranlar bu basit modele oldukça yakın. S2'de beklenenden az bekleme gördük; 30 basışla bunun rastlantı mı yoksa gerçek bir etki mi olduğunu söyleyemiyoruz. Tek bir beklemenin üst sınırı da bir mesaj süresi (≈ 5,6 ms). Gözlenen en uzun beklemeler (2,701 / 5,106 / 5,038 ms) bu sınırın altında kaldı.

Sonuç olarak telemetri tek başına sistemi deadline'a yaklaştırmadı. S0–S3'teki en kötü gözlem 10,730 ms (S2) oldu ve bütün olaylar 20 ms'nin altında kaldı.

### 5.2 CPU yükünün etkisi (S3 → S4 → S5)

CPU yükünde beklentimiz farklıydı. TelemetryTask öncelik 3'te 2 ya da 5 ms hesap yaparken ButtonTask'ın (öncelik 2) CPU'yu bekleyeceğini ve bu yüzden asıl t₁ − t₀'ın büyüyeceğini düşünüyorduk. Bu gerçekten oldu, ama beklediğimiz ölçekte kaldı: t₁ − t₀ ortalaması 0,024 → 0,167 → 0,698 ms'ye çıktı ve en kötü değerler (1,775 ve 4,438 ms) iş süresini hiç aşmadı. Basış işin ortasına denk gelirse ButtonTask işin bitmesini bekliyor, denk gelmezse hiç beklemiyor.

Asıl sürpriz yine t₃ − t₂'deydi. S4'te ortalaması 2,414 ms ile S3'ün biraz üstünde kaldı. S5'te ise 115,472 ms'ye fırladı. S5'in grafiği (4.1) diğerlerinden tamamen farklı görünüyor: R ilk basışta 19,2 ms, sonra her basışta yaklaşık 10 ms artıyor ve 15. olaydan sonra ≈ 163 ms'de sabitleniyor. 28 başarılı olayın 27'si deadline'ı kaçırdı. İki BTN yanıtı ise hiç gönderilemedi (`tx_drop`). Kart aynı senaryoda 14 TEL mesajını da düşürdü.

Bu davranışı ilk olarak kuru denemede gördük ve nedenini ölçümden önce çözmeye çalıştık. S5'te her 10 ms'lik periyodun ilk ≈ 5 ms'sinde TelemetryTask hesap yapıyor. UartTxTask en düşük öncelikte olduğu için, bir mesajın gönderimi bu sırada biterse sıradaki mesaja ancak hesap bittikten sonra başlayabiliyor. Bu arada UART hattı boşta bekliyor. Sonuçta hat periyot başına yalnızca bir mesaj gönderebiliyor. Telemetri de periyot başına tam bir mesaj ürettiği için kuyrukta boşalacak yer kalmıyor ve her BTN mesajı kalıcı bir fazlalık olarak birikiyor. Kuyruk 16 mesaj dolunca (16 × 10 ms ≈ 160 ms) plato oluşuyor ve yeni gelen mesajlar düşürülmeye başlıyor.

Bu açıklamayı destekleyen en güçlü kanıt t₃'lerin zamanlaması oldu. S5'teki 28 başarılı olayın hepsinde t₃, 10 ms'lik periyodun 7183–7190 µs aralığına düşüyor. Yani UART gönderimi her seferinde periyodun aynı 7 µs'lik diliminde başlıyor: hesabın bittiği anda. Aynı bant S3'te 4740–8361 µs, S4'te 6743–8820 µs genişliğindeydi. Yük arttıkça UartTxTask'ın çalışabildiği zaman aralığı gözle görülür şekilde daralıyor.

## 6. Değerlendirme

Bu ölçümden çıkardığımız en önemli sonuç, gecikmenin beklediğimiz yerde değil, bir aşama sonra birikmesiydi. CPU yükü eklediğimizde t₁ − t₀'ın büyümesini bekliyorduk ve büyüdü. Ama bu artış en fazla birkaç milisaniyede kaldı. Sistemi deadline'ın çok ötesine taşıyan şey, yanıtın TX kuyruğunda beklediği t₃ − t₂ oldu. t₂ − t₁ ve hat süresi t₄ − t₃ ise hiçbir senaryoda değişmedi. Bu da yanıt hazırlamanın ve fiziksel iletimin sorun olmadığını gösteriyor.

Bunun iki nedeni var ve ikisi birlikte etkili oluyor. Birincisi, BTN yanıtı ile TEL mesajları aynı FIFO kuyrukta, aralarında hiçbir öncelik farkı olmadan sıraya giriyor. Butona basan kullanıcının yanıtı, kuyrukta onun önünde bekleyen telemetri kadar gecikiyor. İkincisi, UART'ın tek sahibi en düşük öncelikli görev. Hattın kapasitesi aslında yeterliydi: S5'te bile doluluk %55,6 idi. Ama UartTxTask CPU'yu alamadığı sürece hat boş bekliyor. Kısacası darboğaz UART'ın kendisi değil, UART'ı süren görevin önceliği.

Bu yorumu dört ölçüme dayandırıyoruz: bölüm 3'teki aşama tablosu, S5'te t₃'lerin 7 µs'lik tek bir faz bandında toplanması, S5 platosunun kuyruk uzunluğu × periyot hesabıyla (≈ 160 ms) örtüşmesi ve kartın düşürülen mesajları sayan sayaçları (`tx_drop_tel = 14`, `tx_drop_btn = 2`).

Bilmediğimiz şeyler de var. En başta, olası düzeltmelerin hiçbirini denemedik. UartTxTask'ın önceliğini yükseltmek, BTN yanıtları için ayrı ya da öncelikli bir kuyruk kullanmak, UART'ı DMA ile sürmek ya da kuyruk dolmaya başladığında TEL mesajlarını atlamak bu sorunu büyük ihtimalle çözer. Ama hangisinin ne kadar iyileştireceğini ancak yeni bir ölçüm gösterebilir. Ayrıca S5'teki ortalama ve medyan, senaryonun sabit bir özelliği değil: sistem doyuma ulaştıktan sonra R, kaç kez basıldığına bağlı. 60 basış yapsaydık ortalama farklı çıkardı. Bu yüzden S5 için ortalamadan çok platoyu anlamlı buluyoruz. Son olarak ölçümler Debug (`-O0`) derlemesiyle alındı. Optimizasyonlu bir derlemede yazılım aşamaları kısalır, ama S5'teki birikim mekanizmasının değişmeyeceğini düşünüyoruz, çünkü o mekanizma kodun hızından değil görev önceliklerinden kaynaklanıyor.

## 7. Ölçümün Sınırları

- Gözlenen maksimum, kanıtlanmış worst-case değildir. Her senaryoda 30–35 olay ölçüldü.
- t₀, fiziksel basış anı değil, filtrenin kabul ettiği kenarın ISR giriş zamanıdır. Buton hattındaki donanım gecikmesi (varsa RC filtre) t₀'dan önce kalır ve R'ye dahil değildir.
- t₃, ilk fiziksel bitin çıktığı an değildir. t₄ kesme gözlem gecikmesini içerir. t₄ − t₃ ile teorik hat süresi (5,556 ms) arasındaki ≈ 3–4 µs fark bu ek süreleri gösterir.
- Kayıp yanıtlar "deadline karşılandı" olarak sayılmamıştır.
- Firmware Debug (`-O0`) yapılandırmasıyla derlendi. Yazılım aşamalarının mutlak süreleri optimizasyonlu derlemede farklı olur.
- S5 ortalamaları doyum rejiminde basış sayısına bağlıdır (bkz. bölüm 6).
- Basış aralıkları elle üretildi. Aralıkların düzensizliği ölçülmedi, yalnızca PC arayüzü 0,5 s altı basışlarda uyarı verdi.
- `bounce_rejected = 0`: test edilen basışlarda filtreye takılan kenar gözlenmedi. Bu, kartın buton devresi hakkında bir iddia değildir.
