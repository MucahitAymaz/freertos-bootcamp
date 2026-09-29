#include <inttypes.h>
#include <stdbool.h>
#include "app_main.h"
#include "app_config.h"
#include "app_button.h"
#include "app_eventlog.h"
#include "app_time.h"
#include "app_uart.h"
#include "main.h"   /* B1_Pin */

/* Filter state, touched only by the EXTI ISR */
static uint32_t s_next_id = 1U;
static uint32_t s_last_accept_us;
static bool     s_have_accept;

void button_reset(void)
{
    s_next_id     = 1U;
    s_have_accept = false;
}

/* EXTI ISR path: timestamp, filter, record, hand over to ButtonTask. No waiting here. */
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
    if (xQueueSendFromISR(g_btn_queue, &e, &woken) != pdPASS)
    {
        g_cnt.btn_drop++;
        eventlog_set_status(e.id, EV_BTN_DROP);
    }
    portYIELD_FROM_ISR(woken);
}

void ButtonTask(void *argument)
{
    (void)argument;
    ButtonEvent e;
    TxMsg       m;

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
        eventlog_set_ts(e.id, TS_T2, t2);

        if (ok != pdPASS)
        {
            g_cnt.tx_drop_btn++;
            eventlog_set_status(e.id, EV_TX_DROP);
        }
    }
}
