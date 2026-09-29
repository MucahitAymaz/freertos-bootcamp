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
#define UART_TX_TASK_STACK      (512U)

/* ---- UART TX chain ---- */
#define TX_QUEUE_LEN            (16U)     /* TxMsg items, FIFO */
#define MSG_LEN                 (64U)     /* 63 ASCII bytes padded with spaces + '\n' */
#define TX_TIMEOUT_MS           (1000U)   /* max wait for UART TC before abort */

/* ---- UART RX commands ---- */
#define RX_LINE_MAX             (32U)     /* longest accepted command line incl. '\0' */
#define DUMP_LINE_MAX           (384U)    /* DUMP/CNT lines are not bound to 64 bytes */

/* ---- Button chain ---- */
#define BTN_QUEUE_LEN           (8U)      /* ButtonEvent items */
#define BTN_FILTER_US           (30000U)  /* edges within 30 ms of the last accepted one are rejected */

/* ---- Event log ---- */
#define EVENT_LOG_SIZE          (64U)     /* records kept in RAM; more events -> log_overflow */

/* ---- Scenarios: telemetry period and CPU work per period ---- */
typedef struct
{
    uint16_t period_ms;   /* 0 = telemetry off */
    uint16_t work_us;     /* 0 = no extra CPU work */
} ScenarioCfg;

#define SCENARIO_COUNT          (6U)
#define SCENARIO_TABLE                                                  \
    {                                                                   \
        { 0U,   0U    },   /* S0: reference, telemetry off */           \
        { 100U, 0U    },   /* S1: 10 Hz */                              \
        { 20U,  0U    },   /* S2: 50 Hz */                              \
        { 10U,  0U    },   /* S3: 100 Hz */                             \
        { 10U,  2000U },   /* S4: 100 Hz + ~2 ms CPU work */            \
        { 10U,  5000U },   /* S5: 100 Hz + ~5 ms CPU work */            \
    }

/* ---- CPU work calibration ---- */
#define CAL_ITERS               (20000U)  /* iterations timed at startup */
#define CAL_RUNS                (5U)      /* best of N runs, filters ISR noise */

#endif /* APP_CONFIG_H_ */
