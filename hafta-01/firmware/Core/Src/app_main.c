#include "app_main.h"
#include "app_config.h"
#include "app_time.h"
#include "app_uart.h"
#include "app_button.h"
#include "app_eventlog.h"
#include "main.h"   /* Error_Handler() */

QueueHandle_t    g_tx_queue;
QueueHandle_t    g_btn_queue;
volatile uint8_t g_scenario = 0U;
TaskHandle_t     g_task_telemetry;
TaskHandle_t     g_task_button;
TaskHandle_t     g_task_uart;

void app_start(void)
{
    app_time_init();
    eventlog_reset();

    /* Queues first: ISRs and tasks may use them as soon as the scheduler starts */
    g_tx_queue  = xQueueCreate(TX_QUEUE_LEN, sizeof(TxMsg));
    g_btn_queue = xQueueCreate(BTN_QUEUE_LEN, sizeof(ButtonEvent));
    if ((g_tx_queue == NULL) || (g_btn_queue == NULL))
    {
        Error_Handler();
    }

    /* Native FreeRTOS API: stack depth is in words, not bytes */
    if (xTaskCreate(TelemetryTask, "Telemetry", TELEMETRY_TASK_STACK,
                    NULL, TELEMETRY_TASK_PRIO, &g_task_telemetry) != pdPASS)
    {
        Error_Handler();
    }

    if (xTaskCreate(ButtonTask, "Button", BUTTON_TASK_STACK,
                    NULL, BUTTON_TASK_PRIO, &g_task_button) != pdPASS)
    {
        Error_Handler();
    }

    if (xTaskCreate(UartTxTask, "UartTx", UART_TX_TASK_STACK,
                    NULL, UART_TX_TASK_PRIO, &g_task_uart) != pdPASS)
    {
        Error_Handler();
    }
}
