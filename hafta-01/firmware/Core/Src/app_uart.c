#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "app_uart.h"
#include "app_main.h"
#include "app_time.h"
#include "usart.h"
#include "queue.h"

/* Owned by UartTxTask; must not change until TC fires */
static char s_tx_buf[MSG_LEN];

static TaskHandle_t      s_uart_task;
static uint32_t          s_t3;
static volatile uint32_t s_t4;          /* written in TC ISR */
static volatile uint32_t s_last_tx_us;  /* step 2 test only */

/* Temporary counters; moved to the event log module in step 3 */
static volatile uint32_t s_cnt_tx_error;
static volatile uint32_t s_cnt_timeout;
static volatile uint32_t s_cnt_fmt_error;

bool msg_format64(char out[MSG_LEN], const char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    int len = vsnprintf(out, MSG_LEN, fmt, args);
    va_end(args);

    /* Text must fit in 63 bytes; never truncate silently */
    if ((len < 0) || (len > (int)(MSG_LEN - 1U)))
    {
        s_cnt_fmt_error++;
        return false;
    }

    memset(&out[len], ' ', (MSG_LEN - 1U) - (uint32_t)len);
    out[MSG_LEN - 1U] = '\n';
    return true;
}

uint32_t app_uart_last_tx_us(void)
{
    return s_last_tx_us;
}

void UartTxTask(void *argument)
{
    (void)argument;
    TxMsg msg;

    s_uart_task = xTaskGetCurrentTaskHandle();

    for (;;)
    {
        (void)xQueueReceive(g_tx_queue, &msg, portMAX_DELAY);

        if (msg.type == MSG_CMD)
        {
            /* Command handling is added in step 3 */
            continue;
        }

        memcpy(s_tx_buf, msg.data, MSG_LEN);

        /* Drop a stale notification left by a late TC after an earlier timeout */
        (void)ulTaskNotifyTake(pdTRUE, 0);

        s_t3 = timer_us();
        if (HAL_UART_Transmit_IT(&huart2, (uint8_t *)s_tx_buf, MSG_LEN) != HAL_OK)
        {
            s_cnt_tx_error++;
            continue;
        }

        if (ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(TX_TIMEOUT_MS)) == 0U)
        {
            (void)HAL_UART_AbortTransmit(&huart2);
            s_cnt_timeout++;
            continue;
        }

        s_last_tx_us = s_t4 - s_t3;   /* uint32_t subtraction, wrap-safe */
    }
}

/* Called by HAL from the USART2 IRQ when the last stop bit has left the line (TC) */
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance != USART2)
    {
        return;
    }

    s_t4 = timer_us();

    BaseType_t woken = pdFALSE;
    vTaskNotifyGiveFromISR(s_uart_task, &woken);
    portYIELD_FROM_ISR(woken);
}
