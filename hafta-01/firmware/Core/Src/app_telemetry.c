#include <inttypes.h>
#include "app_telemetry.h"
#include "app_main.h"
#include "app_config.h"
#include "app_button.h"
#include "app_eventlog.h"
#include "app_time.h"
#include "app_uart.h"
#include "task.h"

static const ScenarioCfg k_scn[SCENARIO_COUNT] = SCENARIO_TABLE;

static volatile bool     s_running;    /* telemetry produces TEL messages */
static volatile bool     s_restart;    /* scenario changed while running */
static volatile uint32_t s_cal_us;     /* time of CAL_ITERS iterations */
static uint32_t          s_work_iters[SCENARIO_COUNT];

/* Result sink: volatile so the compiler cannot remove the work loop */
static volatile uint32_t s_work_sink;

/* Fixed-iteration integer work (LCG). Interrupts stay enabled, no blocking. */
static void cpu_work(uint32_t iters)
{
    uint32_t x = s_work_sink;
    for (uint32_t i = 0U; i < iters; i++)
    {
        x = (x * 1664525UL) + 1013904223UL;
    }
    s_work_sink = x;
}

/* Times CAL_ITERS iterations with TIM2 and derives iteration counts per scenario */
static void calibrate(void)
{
    uint32_t best = STAT_UNSET;
    for (uint32_t run = 0U; run < CAL_RUNS; run++)
    {
        uint32_t t0 = timer_us();
        cpu_work(CAL_ITERS);
        uint32_t dt = timer_us() - t0;
        if (dt < best)
        {
            best = dt;   /* shortest run = least disturbed by interrupts */
        }
    }
    if (best == 0U)
    {
        best = 1U;
    }
    s_cal_us = best;

    for (uint32_t s = 0U; s < SCENARIO_COUNT; s++)
    {
        s_work_iters[s] = (uint32_t)(((uint64_t)k_scn[s].work_us * CAL_ITERS) / best);
    }
}

bool telemetry_set_scenario(uint8_t scn)
{
    if (scn >= SCENARIO_COUNT)
    {
        return false;
    }

    /* EXTI and USART ISRs are masked here, so no event can hit a half-cleared log */
    taskENTER_CRITICAL();
    g_scenario = scn;
    eventlog_reset();
    button_reset();
    s_restart = true;
    s_running = (k_scn[scn].period_ms != 0U);
    taskEXIT_CRITICAL();

    xTaskNotifyGive(g_task_telemetry);
    return true;
}

void telemetry_stop(void)
{
    s_running = false;
}

bool telemetry_is_running(void)
{
    return s_running;
}

uint32_t telemetry_cal_us(void)
{
    return s_cal_us;
}

void TelemetryTask(void *argument)
{
    (void)argument;
    TickType_t last    = 0U;
    uint32_t   prev_us = 0U;
    bool       first   = true;
    uint32_t   seq     = 0U;
    TxMsg      m;

    calibrate();

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

        if (!s_running)
        {
            continue;
        }
        if (s_restart)
        {
            /* New scenario while running: restart the period from here */
            s_restart = false;
            last  = xTaskGetTickCount();
            first = true;
            seq   = 0U;
            continue;
        }

        /* Measured period: wake-to-wake with the us timer */
        if (!first)
        {
            uint32_t p = now - prev_us;
            if (p < g_cnt.tel_period_min_us) { g_cnt.tel_period_min_us = p; }
            if (p > g_cnt.tel_period_max_us) { g_cnt.tel_period_max_us = p; }
        }
        prev_us = now;
        first   = false;

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
            /* Queue level only rises right after a send, so sampling here catches the peak.
               A failed send means the queue was full at that moment. */
            uint32_t level = TX_QUEUE_LEN;
            if (xQueueSend(g_tx_queue, &m, 0) != pdPASS)
            {
                g_cnt.tx_drop_tel++;
            }
            else
            {
                level = (uint32_t)uxQueueMessagesWaiting(g_tx_queue);
            }
            if (level > g_cnt.txq_hwm_tel)
            {
                g_cnt.txq_hwm_tel = level;
            }
        }
        seq++;
    }
}
