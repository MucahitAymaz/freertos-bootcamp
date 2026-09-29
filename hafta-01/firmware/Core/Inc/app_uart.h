#ifndef APP_UART_H_
#define APP_UART_H_

#include <stdint.h>
#include <stdbool.h>
#include "app_config.h"

typedef enum
{
    MSG_TEL = 0,
    MSG_BTN,
    MSG_CMD       /* received command line, '\0'-terminated in data[] */
} MsgType;

/* Queue item: carries the message bytes themselves, not a pointer */
typedef struct
{
    MsgType  type;
    uint32_t event_id;
    char     data[MSG_LEN];
} TxMsg;

/* Formats a fixed 64-byte line: text, space padding, '\n' at the end.
   Returns false (fmt_error++) if the text does not fit in 63 bytes. */
bool msg_format64(char out[MSG_LEN], const char *fmt, ...);

#endif /* APP_UART_H_ */
