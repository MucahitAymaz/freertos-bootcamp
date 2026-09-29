# Kod Notları

Kritik kod blokları ve çalışma biçimleri. Kod blokları `olcum-v2` tag'indeki (`5baf768`) gerçek kaynak dosyalardan alınmıştır. Satır numaraları o sürüme aittir.

> Not: Bu belgenin taslağı gerçek kaynak dosyalardan Claude ile çıkarıldı (bkz. [ai-usage.md](ai-usage.md)). Açıklamalar kullanıcı tarafından gözden geçirilecek.

Genel yerleşim:

| Dosya | İçerik |
|---|---|
| `Core/Inc/app_config.h` | Bütün sabitler: öncelikler, yığın boyları, kuyruk boyları, filtre süresi, senaryo tablosu |
| `Core/Src/app_main.c` | `app_start()`: kuyrukları ve üç görevi oluşturur (`freertos.c` → `RTOS_THREADS` bloğundan çağrılır) |
| `Core/Src/app_time.c` | `timer_us()` = `TIM2->CNT` |
| `Core/Src/app_button.c` | EXTI callback (ISR yolu) ve ButtonTask |
| `Core/Src/app_telemetry.c` | TelemetryTask, senaryo yönetimi, kalibre CPU işi |
| `Core/Src/app_uart.c` | UartTxTask, TC ve RX callback'leri, komutlar, DUMP |
| `Core/Src/app_eventlog.c` | Olay kayıtları ve sayaçlar |

## 1. Buton ISR ve 30 ms Filtre

Kaynak: [`app_button.c`](../firmware/Core/Src/app_button.c) → `HAL_GPIO_EXTI_Callback` (satır 23–62)

```c
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    uint32_t now = timer_us();   /* t0: first line */

    if (GPIO_Pin != B1_Pin)
    {
        return;
    }

    /* Accept the first edge; reject edges within 30 ms of the last accepted one */
    if (s_have_accept && ((now - s_last_accept_us) < BTN_FILTER_US))
    {
        g_cnt.bounce_rejected++;
        return;
    }
    s_last_accept_us = now;
    s_have_accept    = true;

    ButtonEvent e;
    e.id = s_next_id++;
    e.t0 = now;
    (void)eventlog_open(e.id, now);

    BaseType_t woken = pdFALSE;
    uint32_t level = BTN_QUEUE_LEN;
    if (xQueueSendFromISR(g_btn_queue, &e, &woken) != pdPASS)
    {
        g_cnt.btn_drop++;
        eventlog_set_status(e.id, EV_BTN_DROP);
    }
    else
    {
        level = (uint32_t)uxQueueMessagesWaitingFromISR(g_btn_queue);
    }
    if (level > g_cnt.btnq_hwm)
    {
        g_cnt.btnq_hwm = level;
    }
    portYIELD_FROM_ISR(woken);
}
```

- **t₀ nereden, ne zaman:** Fonksiyonun ilk satırında `timer_us()` ile, yani TIM2'den (32-bit, 1 MHz) alınır. HAL, `EXTI15_10_IRQHandler` → `HAL_GPIO_EXTI_IRQHandler(B1_Pin)` üzerinden kesme bayrağını temizleyip bu callback'i çağırır. t₀ fiziksel basış anı değil, filtrenin kabul ettiği düşen kenarın ISR'e giriş zamanıdır.
- **Filtre:** İlk kenar hiç beklemeden kabul edilir, çünkü `s_have_accept` bayrağı ilk olayı ayrı ele alır. Son kabulden sonraki 30 ms içinde gelen kenarlar `bounce_rejected` sayacına yazılıp atılır. Filtre bir kilitleme (lockout), gecikme değil. Yanıt süresine bir şey eklemez.
- **Olay kimliği:** `s_next_id` 1'den başlar ve `SCN` komutuyla sıfırlanır. Kayıt, kuyruğa göndermeden **önce** açılır. Kuyruk dolu olsa bile olayın kimliği ve t₀'ı kayıtta korunur ve durumu `btn_drop` olur.
- **`xQueueSendFromISR`:** ISR asla beklemez. Kuyruk doluysa hemen hata döner ve kayıp sayılır. Kuyruğa olayın **kopyası** (id + t₀) konur, işaretçi değil.
- **`portYIELD_FROM_ISR(woken)`:** Kuyrukta bekleyen ButtonTask uyandıysa ve o an çalışan görevden daha yüksek öncelikliyse, ISR biter bitmez doğrudan ButtonTask'a geçilir. Bir sonraki tick beklenmez.
- **IRQ önceliği:** `EXTI15_10_IRQn` NVIC önceliği 5. Bu, `configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY` (5) sınırının içinde olduğu için `...FromISR` API'leri güvenle çağrılabilir (CubeMX'te "Uses FreeRTOS functions" ✔).
- ISR'de bekleme, UART yazma ya da `printf` yok.

## 2. TelemetryTask (öncelik 3)

Kaynak: [`app_telemetry.c`](../firmware/Core/Src/app_telemetry.c) → `TelemetryTask` (satır 104–177), `cpu_work` (22–30), `calibrate` (33–56)

```c
    for (;;)
    {
        if (!s_running)
        {
            /* S0 or STOP: block until an SCN command wakes us */
            (void)ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
            s_restart = false;
            last  = xTaskGetTickCount();
            first = true;
            seq   = 0U;
            continue;
        }

        uint8_t scn = g_scenario;
        vTaskDelayUntil(&last, pdMS_TO_TICKS(k_scn[scn].period_ms));
        uint32_t now = timer_us();
        ...
        /* S4/S5: calibrated CPU work, real duration measured every time */
        if (s_work_iters[scn] != 0U)
        {
            uint32_t w0 = timer_us();
            cpu_work(s_work_iters[scn]);
            uint32_t dw = timer_us() - w0;
            if (dw < g_cnt.work_min_us) { g_cnt.work_min_us = dw; }
            if (dw > g_cnt.work_max_us) { g_cnt.work_max_us = dw; }
        }

        m.type     = MSG_TEL;
        m.event_id = seq;
        if (msg_format64(m.data, "TEL,%" PRIu32 ",S%u,%" PRIu32,
                         seq, (unsigned)scn, (uint32_t)xTaskGetTickCount()))
        {
            uint32_t level = TX_QUEUE_LEN;
            if (xQueueSend(g_tx_queue, &m, 0) != pdPASS)
            {
                g_cnt.tx_drop_tel++;
            }
            ...
        }
        seq++;
    }
```

```c
static void cpu_work(uint32_t iters)
{
    uint32_t x = s_work_sink;
    for (uint32_t i = 0U; i < iters; i++)
    {
        x = (x * 1664525UL) + 1013904223UL;
    }
    s_work_sink = x;
}
```

- **Periyot:** `vTaskDelayUntil(&last, pdMS_TO_TICKS(periyot))` bir önceki uyanıştan itibaren sayar. Görevin kendi çalışma süresi (S5'te ≈ 5 ms iş) periyoda eklenmez. `configTICK_RATE_HZ = 1000` olduğu için `pdMS_TO_TICKS(10)` = 10 tick. Projedeki FreeRTOS 10.3.1'de `xTaskDelayUntil` henüz yok. `vTaskDelayUntil` aynı işi yapar, yalnızca bir dönüş değeri yok. Gerçek periyot her uyanışta TIM2 ile ölçülüp `tel_period_min_us` / `tel_period_max_us` sayaçlarına yazılır.
- **S0 ve STOP:** Görev boş döngüde dönmez, `ulTaskNotifyTake(pdTRUE, portMAX_DELAY)` ile bloklanır ve CPU kullanmaz. `SCN` komutu `xTaskNotifyGive` ile uyandırır.
- **CPU işi:** Sabit iterasyonlu bir tamsayı LCG döngüsü. Sonuç `volatile` bir değişkene (`s_work_sink`) yazıldığı için derleyici döngüyü silemez. Kesmeler açık kalır, `vTaskDelay` kullanılmaz. Açılışta `calibrate()` 20 000 iterasyonu TIM2 ile 5 kez ölçer ve en kısa süreyi alır; kesmeler bir ölçümü ancak uzatabilir, bu yüzden en kısası işe en yakın olanıdır. Senaryonun iterasyon sayısı `hedef_µs × 20000 / ölçülen_µs` ile hesaplanır. Her çalışmada gerçek süre yeniden ölçülür (S4: 2002–2063 µs, S5: 5002–5088 µs).
- **TEL mesajı:** `msg_format64` ile 63 bayt ASCII + boşluk dolgusu + `\n` = 64 bayt.
- **Kuyruk doluysa:** `xQueueSend(..., 0)` hiç beklemez, kayıp `tx_drop_tel` sayacına yazılır. En yüksek öncelikli görevin kuyrukta beklemesi sistemi tıkayacağı için bekleme süresi 0.

## 3. ButtonTask (öncelik 2)

Kaynak: [`app_button.c`](../firmware/Core/Src/app_button.c) → `ButtonTask` (satır 64–99)

```c
    for (;;)
    {
        (void)xQueueReceive(g_btn_queue, &e, portMAX_DELAY);
        eventlog_set_ts(e.id, TS_T1, timer_us());

        m.type     = MSG_BTN;
        m.event_id = e.id;
        if (!msg_format64(m.data, "BTN,%" PRIu32 ",S%u,PRESSED", e.id, (unsigned)g_scenario))
        {
            eventlog_set_status(e.id, EV_TX_ERROR);
            continue;
        }

        uint32_t t2 = timer_us();   /* t2: right before xQueueSend */
        BaseType_t ok = xQueueSend(g_tx_queue, &m, 0);
        uint32_t level = (ok == pdPASS) ? (uint32_t)uxQueueMessagesWaiting(g_tx_queue)
                                        : TX_QUEUE_LEN;   /* failed send: queue was full */
        eventlog_set_ts(e.id, TS_T2, t2);
        ...
        if (ok != pdPASS)
        {
            g_cnt.tx_drop_btn++;
            eventlog_set_status(e.id, EV_TX_DROP);
        }
    }
```

- **t₁:** `xQueueReceive` döndükten hemen sonra alınır. t₁ − t₀; ISR'in bitişini, bağlam geçişini ve ButtonTask'ın CPU'yu beklediği süreyi (S4/S5'te TelemetryTask'ın işi) içerir.
- **BTN yanıtı:** Olay kimliğini ve senaryoyu taşıyan 64 baytlık mesaj. Mesaj verinin kendisini taşır (`char data[64]`), yerel bir tamponun adresini değil.
- **t₂:** `xQueueSend` çağrısından **hemen önce** yerel bir değişkene alınır ve kayda gönderimden sonra yazılır. Böylece kayıt işleminin süresi aşamalara karışmaz.
- **Gönderim başarısızsa:** Olay `tx_drop` olarak işaretlenir. t₃ ve t₄ hiç yazılmaz, DUMP'ta boş alan olarak görünür.
- Kuyruk seviyesi gönderimden hemen sonra okunur (`txq_hwm_btn`). Seviye yalnızca gönderimlerle arttığı için zirve kaçmaz.

## 4. UartTxTask (öncelik 1) ve TC Tamamlanması

Kaynak: [`app_uart.c`](../firmware/Core/Src/app_uart.c) → `uart_send` (satır 46–74), `UartTxTask` (200–230), `HAL_UART_TxCpltCallback` (233–250)

```c
static EventStatus uart_send(const char *buf, uint16_t len, uint32_t btn_id)
{
    /* Drop a stale notification left by a late TC after an earlier timeout */
    (void)ulTaskNotifyTake(pdTRUE, 0);
    s_cur_btn_id = btn_id;

    uint32_t t3 = timer_us();   /* t3: right before HAL_UART_Transmit_IT */
    if (HAL_UART_Transmit_IT(&huart2, (uint8_t *)buf, len) != HAL_OK)
    {
        s_cur_btn_id = 0U;
        g_cnt.tx_error++;
        return EV_TX_ERROR;
    }
    if (btn_id != 0U)
    {
        eventlog_set_ts(btn_id, TS_T3, t3);
    }

    if (ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(TX_TIMEOUT_MS)) == 0U)
    {
        (void)HAL_UART_AbortTransmit(&huart2);
        s_cur_btn_id = 0U;
        g_cnt.timeout++;
        return EV_TIMEOUT;
    }

    s_cur_btn_id = 0U;
    return EV_OK;
}
```

```c
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance != USART2)
    {
        return;
    }

    uint32_t now = timer_us();   /* t4 */
    uint32_t id  = s_cur_btn_id;
    if (id != 0U)
    {
        eventlog_set_ts(id, TS_T4, now);
    }

    BaseType_t woken = pdFALSE;
    vTaskNotifyGiveFromISR(s_uart_task, &woken);
    portYIELD_FROM_ISR(woken);
}
```

- **UART'ın tek sahibi:** Yalnızca UartTxTask `HAL_UART_Transmit_IT` çağırır. Diğer görevler mesajlarını TX kuyruğuna (16 × `TxMsg`, FIFO) bırakır. Görev mesajı kuyruktan alır, **kendi statik tamponuna** (`s_tx_buf`) kopyalar ve gönderir.
- **t₃:** `HAL_UART_Transmit_IT` çağrısından hemen önce. İlk fiziksel bitin çıktığı an değildir.
- **Başlatma başarısızsa:** `HAL_OK` dönmezse olay `tx_error` olur ve görev beklemeden bir sonraki mesaja geçer.
- **t₄ ve uyandırma:** HAL, IT modunda son baytı yazdıktan sonra TC (transmission complete) kesmesini açar. TC, son stop biti hattan çıktığında gelir ve HAL `HAL_UART_TxCpltCallback`'i çağırır. t₄ callback'in ilk işlemi olarak alınır. Görev `vTaskNotifyGiveFromISR` ile uyandırılır. Task notification ayrı bir kuyruk ya da semaphore nesnesi gerektirmeyen en hafif uyandırma yoludur.
- **Tamponun ömrü:** `s_tx_buf` statiktir ve görev TC bildirimi gelene ya da timeout olana kadar bloklu beklediği için bu sürede değişmez. Gönderim arka planda kesmelerle devam ederken tamponun üzerine yazılmaz.
- **"DMA bitti" ile "son bit çıktı" farkı:** DMA'nın tamamlanma kesmesi yalnızca son baytın UART veri yazmacına taşındığını gösterir; o bayt hâlâ hattan çıkmaktadır. Bu projede DMA kullanılmadı. t₄, UART'ın kendi TC olayından alınıyor, yani son bitin gerçekten çıktığı anı gösteriyor. Ölçülen t₄ − t₃ = 5,559 ms, teorik hat süresine (64 × 10 / 115200 = 5,556 ms) yalnızca ≈ 3 µs uzak.
- **Timeout (1 s):** `ulTaskNotifyTake` 0 dönerse `HAL_UART_AbortTransmit` ile aktarım güvenle sonlandırılır ve olay `timeout` olur. Gönderimden önceki `ulTaskNotifyTake(pdTRUE, 0)` çağrısı, geç gelmiş bir TC'nin bıraktığı eski bildirimi temizler. Temizlenmese bir sonraki mesajda görev hiç beklemeden döner ve yanlış bir t₄ − t₃ hesaplanırdı.

## 5. Olay Kayıtları

Kaynak: [`app_eventlog.h`](../firmware/Core/Inc/app_eventlog.h) (kayıt yapısı), [`app_eventlog.c`](../firmware/Core/Src/app_eventlog.c) (satır 7–44)

```c
typedef struct
{
    uint32_t id;
    uint32_t t[TS_COUNT];
    uint8_t  has[TS_COUNT];   /* 1 = timestamp taken; a missing one is never written as 0 */
    uint8_t  status;          /* EventStatus */
} EventRecord;
```

```c
static EventRecord       s_log[EVENT_LOG_SIZE];
static volatile uint32_t s_count;

static EventRecord *record(uint32_t id)
{
    if ((id == 0U) || (id > EVENT_LOG_SIZE))
    {
        return NULL;
    }
    return &s_log[id - 1U];
}

bool eventlog_open(uint32_t id, uint32_t t0)
{
    EventRecord *r = record(id);
    if (r == NULL)
    {
        g_cnt.log_overflow++;
        return false;
    }

    memset(r, 0, sizeof(*r));
    r->id           = id;
    r->t[TS_T0]     = t0;
    r->has[TS_T0]   = 1U;
    r->status       = (uint8_t)EV_PENDING;
    s_count         = id;
    return true;
}
```

- **Yapı:** Olay kimliği, beş zaman damgası (t₀–t₄), her damga için bir "alındı" bayrağı (`has[]`) ve durum (`ok`, `btn_drop`, `tx_drop`, `tx_error`, `timeout`; zincir bitmemişse `pending`).
- **Kapasite:** RAM'de 64 kayıt (`EVENT_LOG_SIZE`). Daha fazla olay gelirse kayıt açılmaz ve `log_overflow` sayacı artar.
- **Kimlikle eşleştirme:** N numaralı olayın kaydı dizinin N−1. elemanında durur. Arama yok, sabit sürede erişim var ve ISR'den güvenle çağrılabiliyor. Tek bir global timestamp değişkeni kullanılmıyor. Her bağlam damgasını olay kimliğiyle kaydediyor: t₀ EXTI ISR, t₁–t₂ ButtonTask, t₃ UartTxTask, t₄ TC ISR (`s_cur_btn_id` üzerinden). Zincir doğası gereği sıralı olduğu için aynı alana iki bağlam aynı anda yazmıyor. `has[]` bayt dizisi, çünkü bayt yazma atomik.
- **Sayaçlar:** Her sayacın yalnızca **bir** yazan bağlamı var (ör. `bounce_rejected` → EXTI ISR, `tx_drop_tel` → TelemetryTask). Bu yüzden kilit olmadan artırılabiliyorlar.
- **Sıfırlama:** `SCN` komutu kayıtları, sayaçları ve olay kimliğini `taskENTER_CRITICAL()` içinde sıfırlar. EXTI ve USART kesmeleri bu kısa sürede maskelenir; bir ISR yarım temizlenmiş bir tabloya yazamaz.
- **Dışarı aktarma:** `STOP` komutundan sonra `DUMP` ile. Telemetri çalışırken `DUMP` reddedilir (`ERR,DUMP needs STOP first`). Ölçüm sırasında sayaçlar sürekli yazdırılmaz.

## 6. Zaman Hesapları

- **Timer:** TIM2, 32-bit, APB1 timer saati 80 MHz, PSC = 79 → 1 MHz → **1 µs çözünürlük**. Taşma süresi 2³² µs ≈ **71,6 dakika**. Sayaç `app_time_init()` içinde `HAL_TIM_Base_Start` ile, kesme olmadan başlatılır.
- **Farklar:** Bütün farklar `uint32_t` çıkarmasıyla (mod 2³²) hesaplanır: firmware'de `now - s_last_accept_us`, analizde `(b - a) & 0xFFFFFFFF`. Sayaç iki damga arasında bir kez taşsa bile sonuç doğru çıkar. Bir olayın süresi bir sayaç turundan (71,6 dk) çok kısa olduğu için bu yeterli.
- **Eksik zamanlar:** Alınmamış bir damga 0 olarak yazılmaz. `has[]` bayrağıyla işaretlenir ve DUMP'ta **boş alan** olarak gönderilir (ör. `tx_drop` satırında t₃ ve t₄ boş). Analiz betiği bu olayları zaman istatistiklerinden dışlar ve nedenini raporlar.
- **Duvar saati:** Bütün aralıklar duvar saati süreleridir. Aradaki kesmeler ve yüksek öncelikli görevler de aralığa dahildir. CPU süresi ölçülmez.

## 7. Mesaj Biçimi

| Tür | Örnek içerik | Boyut |
|---|---|---|
| TEL | `TEL,<seq>,<scn>,<tick_ms>` → `TEL,1042,S3,726` + boşluklar + `\n` | 64 bayt (63 + LF) |
| BTN | `BTN,<event_id>,<scn>,PRESSED` → `BTN,17,S3,PRESSED` + boşluklar + `\n` | 64 bayt (63 + LF) |
| Kayıt aktarımı (DUMP) | Başlık, olay satırları, `CNT,...`, `END` (aşağıda) | Değişken, 64 bayt kuralına tabi değil |
| Komut yanıtları | `ACK,SCN,S3` · `ACK,STOP` · `ERR,...` | Değişken |

64 bayt biçimleme [`msg_format64`](../firmware/Core/Src/app_uart.c) ile yapılır: `vsnprintf` metni yazar, metin 63 baytı aşarsa **kesilmez**, `fmt_error` sayacı artar ve mesaj gönderilmez. Sığıyorsa kalan yer boşlukla doldurulur ve 64. bayta `\n` konur. PC arayüzü her TEL/BTN satırının uzunluğunu kontrol eder ("64 bayt dışı satır" sayacı).

Gerçek bir DUMP çıktısından örnek satırlar (`measurements/S0.csv`, `S5.csv`):

```
scenario,event_id,t0_us,t1_us,t2_us,t3_us,t4_us,status
S0,1,14252449,14252474,14252511,14252569,14258128,ok
S5,1,167979328,167980189,167980226,167990191,167995750,ok
S5,18,178008355,178010189,178010226,,,tx_drop
```

Son satırda BTN yanıtı TX kuyruğuna giremediği için t₃ ve t₄ alınmadı ve boş bırakıldı. Sayaç satırı `key=value` biçimindedir. Arayüz bunu `Sx_counters.csv` olarak ayrı kaydeder:

```
CNT,bounce_rejected=0,btn_drop=0,tx_drop_tel=12,tx_drop_btn=12,tx_error=0,timeout=0,log_overflow=0,...,txq_hwm=16,txq_hwm_tel=16,txq_hwm_btn=16,btnq_hwm=1
END
```

Komutlar (PC → kart, `\r` ya da `\n` ile biten satır): `SCN,S0` … `SCN,S5`, `STOP`, `DUMP`. RX kesmesi satırı biriktirir ve tamamlanan satırı `MSG_CMD` tipli bir `TxMsg` olarak TX kuyruğuna koyar. Komut da UART'ın tek sahibi olan UartTxTask'ta işlenir; dördüncü bir görev yoktur.
