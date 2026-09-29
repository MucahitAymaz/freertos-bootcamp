#include "app_main.h"
#include "app_config.h"
#include "main.h"   /* LD2 pin definitions */

void TelemetryTask(void *argument)
{
    (void)argument;

    for (;;)
    {
        /* Step 1 heartbeat only: real telemetry and scenarios arrive in step 4 */
        HAL_GPIO_TogglePin(LD2_GPIO_Port, LD2_Pin);
        vTaskDelay(pdMS_TO_TICKS(LED_TEST_PERIOD_MS));
    }
}
