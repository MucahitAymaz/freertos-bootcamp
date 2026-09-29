#include <string.h>
#include "app_eventlog.h"

volatile Counters g_cnt;

/* Record for event id N lives at index N-1: no search, safe to call from an ISR */
static EventRecord       s_log[EVENT_LOG_SIZE];
static volatile uint32_t s_count;

static EventRecord *record(uint32_t id)
{
    if ((id == 0U) || (id > EVENT_LOG_SIZE))
    {
        return NULL;
    }
    return &s_log[id - 1U];
}

void eventlog_reset(void)
{
    memset(s_log, 0, sizeof(s_log));
    memset((void *)&g_cnt, 0, sizeof(g_cnt));
    s_count = 0U;
}

bool eventlog_open(uint32_t id, uint32_t t0)
{
    EventRecord *r = record(id);
    if (r == NULL)
    {
        g_cnt.log_overflow++;
        return false;
    }

    memset(r, 0, sizeof(*r));
    r->id           = id;
    r->t[TS_T0]     = t0;
    r->has[TS_T0]   = 1U;
    r->status       = (uint8_t)EV_PENDING;
    s_count         = id;
    return true;
}

void eventlog_set_ts(uint32_t id, TsIndex idx, uint32_t t)
{
    EventRecord *r = record(id);
    if (r != NULL)
    {
        r->t[idx]   = t;
        r->has[idx] = 1U;
    }
}

void eventlog_set_status(uint32_t id, EventStatus st)
{
    EventRecord *r = record(id);
    if (r != NULL)
    {
        r->status = (uint8_t)st;
    }
}

uint32_t eventlog_count(void)
{
    return s_count;
}

const EventRecord *eventlog_get(uint32_t id)
{
    return record(id);
}

const char *eventlog_status_name(uint8_t st)
{
    switch ((EventStatus)st)
    {
        case EV_OK:       return "ok";
        case EV_BTN_DROP: return "btn_drop";
        case EV_TX_DROP:  return "tx_drop";
        case EV_TX_ERROR: return "tx_error";
        case EV_TIMEOUT:  return "timeout";
        default:          return "pending";
    }
}
