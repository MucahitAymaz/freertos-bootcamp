#include <inttypes.h>
#include "app_main.h"
#include "app_config.h"
#include "app_uart.h"
#include "main.h"   /* LD2 pin definitions */

/* Step 2 test only: counts test messages the TX queue could not accept */
static volatile uint32_t s_test_tx_drop;

void TelemetryTask(void *argument)
{
    (void)argument;
    uint32_t n = 0U;
    TxMsg    m;

    for (;;)
    {
        /* Step 2 test only: temporary producer, replaced by real telemetry in step 4 */
        m.type     = MSG_TEL;
        m.event_id = n;
        if (msg_format64(m.data, "TEST,%" PRIu32 ",%" PRIu32, n, app_uart_last_tx_us()))
        {
            if (xQueueSend(g_tx_queue, &m, 0) != pdPASS)
            {
                s_test_tx_drop++;
            }
        }
        n++;

        /* Keep the step 1 heartbeat: toggle LD2 every 500 ms */
        if ((n % (LED_TEST_PERIOD_MS / TX_TEST_PERIOD_MS)) == 0U)
        {
            HAL_GPIO_TogglePin(LD2_GPIO_Port, LD2_Pin);
        }

        vTaskDelay(pdMS_TO_TICKS(TX_TEST_PERIOD_MS));
    }
}
