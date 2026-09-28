/*
 * app_config.h
 *
 *  Created on: 28 Eyl 2026
 *      Author: mucahit.aymaz
 */

#ifndef APP_CONFIG_H_
#define APP_CONFIG_H_


#include "FreeRTOS.h"
#include "task.h"

/* ---- Task priorities (higher number = higher priority) ---- */
#define TELEMETRY_TASK_PRIO     (tskIDLE_PRIORITY + 3)
#define BUTTON_TASK_PRIO        (tskIDLE_PRIORITY + 2)
#define UART_TX_TASK_PRIO       (tskIDLE_PRIORITY + 1)

/* ---- Task stack sizes in words (1 word = 4 bytes on Cortex-M4) ---- */
/* Tasks that call snprintf get more stack; verify later with high-water marks */
#define TELEMETRY_TASK_STACK    (512U)
#define BUTTON_TASK_STACK       (512U)
#define UART_TX_TASK_STACK      (256U)

/* ---- UART TX chain ---- */
#define TX_QUEUE_LEN            (16U)     /* TxMsg items, FIFO */
#define MSG_LEN                 (64U)     /* 63 ASCII bytes padded with spaces + '\n' */
#define TX_TIMEOUT_MS           (1000U)   /* max wait for UART TC before abort */

/* ---- Step 2 test only: temporary producer period, removed in step 3 ---- */
#define TX_TEST_PERIOD_MS       (100U)

/* ---- Step 1 test only: LD2 toggle period, removed in step 4 ---- */
#define LED_TEST_PERIOD_MS      (500U)

#endif /* APP_CONFIG_H_ */
