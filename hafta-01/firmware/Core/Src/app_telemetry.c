#include "app_main.h"
#include "app_config.h"
#include "main.h"   /* LD2 pin definitions */

void TelemetryTask(void *argument)
{
    (void)argument;

    for (;;)
    {
        /* Step 1 test only: blink LD2 to prove the scheduler runs. Removed in step 4. */
        HAL_GPIO_TogglePin(LD2_GPIO_Port, LD2_Pin);
        vTaskDelay(pdMS_TO_TICKS(LED_TEST_PERIOD_MS));
    }
}
