#ifndef APP_EVENTLOG_H_
#define APP_EVENTLOG_H_

#include <stdint.h>
#include <stdbool.h>
#include "app_config.h"

typedef enum
{
    EV_PENDING = 0,   /* chain not finished yet */
    EV_OK,
    EV_BTN_DROP,      /* button queue full */
    EV_TX_DROP,       /* TX queue full */
    EV_TX_ERROR,      /* UART could not be started */
    EV_TIMEOUT        /* no TC within TX_TIMEOUT_MS */
} EventStatus;

typedef enum
{
    TS_T0 = 0,        /* EXTI callback, first line */
    TS_T1,            /* ButtonTask, right after xQueueReceive */
    TS_T2,            /* ButtonTask, right before xQueueSend */
    TS_T3,            /* UartTxTask, right before HAL_UART_Transmit_IT */
    TS_T4,            /* TC callback */
    TS_COUNT
} TsIndex;

typedef struct
{
    uint32_t id;
    uint32_t t[TS_COUNT];
    uint8_t  has[TS_COUNT];   /* 1 = timestamp taken; a missing one is never written as 0 */
    uint8_t  status;          /* EventStatus */
} EventRecord;

/* Each counter has exactly one writer context, so plain increments are safe */
typedef struct
{
    uint32_t bounce_rejected;   /* EXTI ISR */
    uint32_t btn_drop;          /* EXTI ISR */
    uint32_t log_overflow;      /* EXTI ISR */
    uint32_t tx_drop_tel;       /* TelemetryTask */
    uint32_t tx_drop_btn;       /* ButtonTask */
    uint32_t tx_error;          /* UartTxTask */
    uint32_t timeout;           /* UartTxTask */
    uint32_t fmt_error;         /* message did not fit in 63 bytes */
    uint32_t cmd_drop;          /* RX ISR: TX queue full for a command */
    uint32_t rx_error;          /* RX ISR: UART error, reception restarted */
    uint32_t tel_period_min_us; /* TelemetryTask: measured wake-to-wake period */
    uint32_t tel_period_max_us;
    uint32_t work_min_us;       /* TelemetryTask: measured CPU work duration */
    uint32_t work_max_us;
    uint32_t txq_hwm_tel;       /* TelemetryTask: highest TX queue level seen after its sends */
    uint32_t txq_hwm_btn;       /* ButtonTask: highest TX queue level seen after its sends */
    uint32_t btnq_hwm;          /* EXTI ISR: highest button queue level seen after its sends */
} Counters;

#define STAT_UNSET              (0xFFFFFFFFUL)   /* min fields before the first sample */

extern volatile Counters g_cnt;

void eventlog_reset(void);

/* Called from the EXTI ISR. Returns false (log_overflow++) when the log is full. */
bool eventlog_open(uint32_t id, uint32_t t0);

void eventlog_set_ts(uint32_t id, TsIndex idx, uint32_t t);
void eventlog_set_status(uint32_t id, EventStatus st);

/* Highest event id that got a record (records are ids 1..count) */
uint32_t eventlog_count(void);
const EventRecord *eventlog_get(uint32_t id);
const char *eventlog_status_name(uint8_t st);

#endif /* APP_EVENTLOG_H_ */
