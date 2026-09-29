#ifndef APP_BUTTON_H_
#define APP_BUTTON_H_

#include <stdint.h>

/* Button queue item, produced by the EXTI callback */
typedef struct
{
    uint32_t id;   /* event id, starts at 1 */
    uint32_t t0;   /* timer_us() at the first line of the EXTI callback */
} ButtonEvent;

#endif /* APP_BUTTON_H_ */
