#include "app_main.h"
#include "app_config.h"
#include "app_time.h"
#include "main.h"   /* Error_Handler() */

void app_start(void)
{
    app_time_init();

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
