#ifndef APP_MAIN_H_
#define APP_MAIN_H_

/* Creates application tasks. Called from freertos.c before the scheduler starts. */
void app_start(void);

/* Task entry points, implemented in their own modules */
void TelemetryTask(void *argument);
void ButtonTask(void *argument);
void UartTxTask(void *argument);

#endif /* APP_MAIN_H_ */
