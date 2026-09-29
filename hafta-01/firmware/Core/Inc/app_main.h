#ifndef APP_MAIN_H_
#define APP_MAIN_H_

#include <stdint.h>
#include "FreeRTOS.h"
#include "queue.h"

/* Shared TX queue: every producer sends TxMsg here, only UartTxTask consumes */
extern QueueHandle_t g_tx_queue;

/* Button queue: EXTI callback produces ButtonEvent, ButtonTask consumes */
extern QueueHandle_t g_btn_queue;

/* Active scenario number (0..5); set by the SCN command in step 4 */
extern volatile uint8_t g_scenario;

/* Creates application queues and tasks. Called from freertos.c before the scheduler starts. */
void app_start(void);

/* Task entry points, implemented in their own modules */
void TelemetryTask(void *argument);
void ButtonTask(void *argument);
void UartTxTask(void *argument);

#endif /* APP_MAIN_H_ */
