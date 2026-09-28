#include "app_main.h"
#include "app_config.h"
#include "app_time.h"
#include "app_uart.h"
#include "main.h"   /* Error_Handler() */

QueueHandle_t g_tx_queue;

void app_start(void)
{
    app_time_init();

    /* Queues first: tasks may use them as soon as the scheduler starts */
    g_tx_queue = xQueueCreate(TX_QUEUE_LEN, sizeof(TxMsg));
    if (g_tx_queue == NULL)
    {
        Error_Handler();
    }

    /* Native FreeRTOS API: stack depth is in words, not bytes */
    if (xTaskCreate(TelemetryTask, "Telemetry", TELEMETRY_TASK_STACK,
                    NULL, TELEMETRY_TASK_PRIO, NULL) != pdPASS)
    {
        Error_Handler();
    }

    if (xTaskCreate(ButtonTask, "Button", BUTTON_TASK_STACK,
                    NULL, BUTTON_TASK_PRIO, NULL) != pdPASS)
    {
        Error_Handler();
    }

    if (xTaskCreate(UartTxTask, "UartTx", UART_TX_TASK_STACK,
                    NULL, UART_TX_TASK_PRIO, NULL) != pdPASS)
    {
        Error_Handler();
    }
}
