#include "app_main.h"
#include "app_config.h"

void ButtonTask(void *argument)
{
    (void)argument;

    for (;;)
    {
        /* Skeleton: must block, never busy-loop. Replaced by xQueueReceive in step 3. */
        vTaskDelay(portMAX_DELAY);
    }
}
