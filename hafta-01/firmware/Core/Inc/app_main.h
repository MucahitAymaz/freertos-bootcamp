#ifndef APP_MAIN_H_
#define APP_MAIN_H_

#include "FreeRTOS.h"
#include "queue.h"

/* Shared TX queue: every producer sends TxMsg here, only UartTxTask consumes */
extern QueueHandle_t g_tx_queue;

/* Creates application queues and tasks. Called from freertos.c before the scheduler starts. */
void app_start(void);

/* Task entry points, implemented in their own modules */
void TelemetryTask(void *argument);
void ButtonTask(void *argument);
void UartTxTask(void *argument);

#endif /* APP_MAIN_H_ */
