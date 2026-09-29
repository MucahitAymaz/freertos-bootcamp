#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "app_uart.h"
#include "app_main.h"
#include "app_eventlog.h"
#include "app_telemetry.h"
#include "app_time.h"
#include "usart.h"

/* Owned by UartTxTask; must not change until TC fires */
static char s_tx_buf[MSG_LEN];
static char s_dump_buf[DUMP_LINE_MAX];

static TaskHandle_t      s_uart_task;
static volatile uint32_t s_cur_btn_id;   /* event id of the frame on the line, 0 = not a BTN frame */

/* RX line assembly, touched only by the RX ISR */
static uint8_t  s_rx_byte;
static char     s_rx_line[RX_LINE_MAX];
static uint32_t s_rx_len;
static bool     s_rx_overflow;

bool msg_format64(char out[MSG_LEN], const char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    int len = vsnprintf(out, MSG_LEN, fmt, args);
    va_end(args);

    /* Text must fit in 63 bytes; never truncate silently */
    if ((len < 0) || (len > (int)(MSG_LEN - 1U)))
    {
        g_cnt.fmt_error++;
        return false;
    }

    memset(&out[len], ' ', (MSG_LEN - 1U) - (uint32_t)len);
    out[MSG_LEN - 1U] = '\n';
    return true;
}

/* Starts one IT transmission and blocks until TC or timeout.
   btn_id != 0 records t3/t4 for that event. */
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

/* DUMP/CNT lines: variable length, not bound to the 64-byte rule */
static void send_line(const char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    int len = vsnprintf(s_dump_buf, sizeof(s_dump_buf), fmt, args);
    va_end(args);

    if ((len < 0) || (len >= (int)sizeof(s_dump_buf)))
    {
        g_cnt.fmt_error++;
        return;
    }
    (void)uart_send(s_dump_buf, (uint16_t)len, 0U);
}

/* Writes value, or an empty string when the stat never got a sample (min still unset) */
static void fmt_stat(char *out, size_t size, uint32_t value, uint32_t min_value)
{
    if (min_value == STAT_UNSET)
    {
        out[0] = '\0';
    }
    else
    {
        (void)snprintf(out, size, "%" PRIu32, value);
    }
}

static void dump_log(void)
{
    char f[TS_COUNT][12];
    uint32_t n = eventlog_count();

    send_line("scenario,event_id,t0_us,t1_us,t2_us,t3_us,t4_us,status\n");

    for (uint32_t id = 1U; id <= n; id++)
    {
        const EventRecord *r = eventlog_get(id);
        if (r == NULL)
        {
            break;
        }
        /* Missing timestamp -> empty field, never 0 */
        for (uint32_t i = 0U; i < TS_COUNT; i++)
        {
            if (r->has[i] != 0U)
            {
                (void)snprintf(f[i], sizeof(f[i]), "%" PRIu32, r->t[i]);
            }
            else
            {
                f[i][0] = '\0';
            }
        }
        send_line("S%u,%" PRIu32 ",%s,%s,%s,%s,%s,%s\n",
                  (unsigned)g_scenario, r->id, f[0], f[1], f[2], f[3], f[4],
                  eventlog_status_name(r->status));
    }

    /* Min/max stats that never got a sample are sent as empty fields */
    char pmin[12], pmax[12], wmin[12], wmax[12];
    fmt_stat(pmin, sizeof(pmin), g_cnt.tel_period_min_us, g_cnt.tel_period_min_us);
    fmt_stat(pmax, sizeof(pmax), g_cnt.tel_period_max_us, g_cnt.tel_period_min_us);
    fmt_stat(wmin, sizeof(wmin), g_cnt.work_min_us, g_cnt.work_min_us);
    fmt_stat(wmax, sizeof(wmax), g_cnt.work_max_us, g_cnt.work_min_us);

    send_line("CNT,bounce_rejected=%" PRIu32 ",btn_drop=%" PRIu32 ",tx_drop_tel=%" PRIu32
              ",tx_drop_btn=%" PRIu32 ",tx_error=%" PRIu32 ",timeout=%" PRIu32
              ",log_overflow=%" PRIu32 ",fmt_error=%" PRIu32 ",cmd_drop=%" PRIu32
              ",rx_error=%" PRIu32
              ",tel_period_min_us=%s,tel_period_max_us=%s,work_min_us=%s,work_max_us=%s"
              ",cal_us=%" PRIu32 ",cal_iters=%u"
              ",hwm_tel_words=%u,hwm_btn_words=%u,hwm_uart_words=%u\n",
              g_cnt.bounce_rejected, g_cnt.btn_drop, g_cnt.tx_drop_tel,
              g_cnt.tx_drop_btn, g_cnt.tx_error, g_cnt.timeout,
              g_cnt.log_overflow, g_cnt.fmt_error, g_cnt.cmd_drop, g_cnt.rx_error,
              pmin, pmax, wmin, wmax,
              telemetry_cal_us(), (unsigned)CAL_ITERS,
              (unsigned)uxTaskGetStackHighWaterMark(g_task_telemetry),
              (unsigned)uxTaskGetStackHighWaterMark(g_task_button),
              (unsigned)uxTaskGetStackHighWaterMark(g_task_uart));
    send_line("END\n");
}

static void handle_command(const char *cmd)
{
    if (strcmp(cmd, "DUMP") == 0)
    {
        /* Records are read while nothing else produces: only after STOP (or in S0) */
        if (telemetry_is_running())
        {
            send_line("ERR,DUMP needs STOP first\n");
            return;
        }
        dump_log();
    }
    else if (strcmp(cmd, "STOP") == 0)
    {
        telemetry_stop();
        send_line("ACK,STOP\n");
    }
    else if ((strncmp(cmd, "SCN,S", 5) == 0) && (cmd[5] >= '0') && (cmd[5] <= '9') && (cmd[6] == '\0'))
    {
        uint8_t scn = (uint8_t)(cmd[5] - '0');
        if (telemetry_set_scenario(scn))
        {
            send_line("ACK,SCN,S%u\n", (unsigned)scn);
        }
        else
        {
            send_line("ERR,unknown scenario\n");
        }
    }
    else
    {
        send_line("ERR,unknown command\n");
    }
}

void UartTxTask(void *argument)
{
    (void)argument;
    TxMsg msg;

    s_uart_task = xTaskGetCurrentTaskHandle();
    (void)HAL_UART_Receive_IT(&huart2, &s_rx_byte, 1U);

    for (;;)
    {
        (void)xQueueReceive(g_tx_queue, &msg, portMAX_DELAY);

        if (msg.type == MSG_CMD)
        {
            handle_command(msg.data);
            continue;
        }

        memcpy(s_tx_buf, msg.data, MSG_LEN);

        if (msg.type == MSG_BTN)
        {
            EventStatus st = uart_send(s_tx_buf, MSG_LEN, msg.event_id);
            eventlog_set_status(msg.event_id, st);
        }
        else
        {
            (void)uart_send(s_tx_buf, MSG_LEN, 0U);
        }
    }
}

/* Called by HAL from the USART2 IRQ when the last stop bit has left the line (TC) */
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

/* One byte received: build a line, hand complete lines to UartTxTask as MSG_CMD */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance != USART2)
    {
        return;
    }

    BaseType_t woken = pdFALSE;
    char c = (char)s_rx_byte;

    if ((c == '\r') || (c == '\n'))
    {
        if (!s_rx_overflow && (s_rx_len > 0U))
        {
            TxMsg m;
            m.type     = MSG_CMD;
            m.event_id = 0U;
            memcpy(m.data, s_rx_line, s_rx_len);
            m.data[s_rx_len] = '\0';
            if (xQueueSendFromISR(g_tx_queue, &m, &woken) != pdPASS)
            {
                g_cnt.cmd_drop++;
            }
        }
        s_rx_len      = 0U;
        s_rx_overflow = false;
    }
    else if (s_rx_len < (RX_LINE_MAX - 1U))
    {
        s_rx_line[s_rx_len++] = c;
    }
    else
    {
        s_rx_overflow = true;   /* too long: discard the whole line */
    }

    (void)HAL_UART_Receive_IT(&huart2, &s_rx_byte, 1U);
    portYIELD_FROM_ISR(woken);
}

/* Overrun or framing error stops IT reception in HAL; restart it */
void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance != USART2)
    {
        return;
    }
    g_cnt.rx_error++;
    s_rx_len      = 0U;
    s_rx_overflow = false;
    (void)HAL_UART_Receive_IT(&huart2, &s_rx_byte, 1U);
}
